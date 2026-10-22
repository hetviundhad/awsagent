import os
import re
import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Response, Request, Depends, status
from fastapi.responses import StreamingResponse

from backend.app.models.schemas import (
    Course, CourseCreate, TutorQueryRequest, TutorQueryResponse,
    AssessmentGenerateRequest, AssessmentSubmitRequest, EvaluationRunRequest,
    ExplainUrlRequest, AddNoteRequest, YouTubeIngestRequest
)
from backend.app.services.database import db
from backend.app.services.storage import storage
from backend.app.services.web_extractor import web_extractor
from backend.app.providers.llm_provider import get_llm_provider
from backend.app.providers.vision_provider import get_vision_provider
from backend.app.ingestion.pipeline import ingestion_pipeline
from backend.app.rag.engine import rag_engine
from backend.app.assessment.generator import assessment_engine
from backend.app.learner.bkt import bkt_engine
from backend.app.evaluation.ragas_eval import evaluation_suite
from backend.app.services.sample_course import load_sample_course_for_user
from backend.app.core.config import settings, is_test_environment
from backend.app.core.errors import AIServiceUnavailableError
from backend.app.evaluation.simulator import synthetic_simulator
from backend.app.api.dependencies import (
    get_student_id_from_request,
    get_owner_id_from_request,
    ensure_course_access,
    DEMO_STUDENT_IDS
)

router = APIRouter()

# --- Learner Model (BKT) ---
@router.get("/learner/{student_id}/mastery")
def get_student_mastery(student_id: str, request: Request, course_id: Optional[str] = None):
    effective_id = get_student_id_from_request(request)
    if student_id and student_id not in ("default_student", "demo", "demo_student") and student_id != effective_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's mastery profile")
    target_id = effective_id if (not student_id or student_id in ("default_student", "demo", "demo_student")) else student_id
    if not course_id:
        return {
            "student_id": target_id,
            "course_id": None,
            "overall_mastery": 0.0,
            "mastery_by_concept": [],
            "concepts_mastered": 0,
            "total_concepts": 0,
            "study_streak_days": 0,
            "due_reviews_count": 0,
            "recommendations": []
        }
    ensure_course_access(db.get_by_id("courses", course_id), target_id)
    profile = bkt_engine.get_learner_profile(target_id, course_id)
    return profile

@router.get("/learner/{student_id}/recommendations")
def get_student_recommendations(student_id: str, request: Request, course_id: Optional[str] = None):
    effective_id = get_student_id_from_request(request)
    if student_id and student_id not in ("default_student", "demo", "demo_student") and student_id != effective_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's recommendations")
    target_id = effective_id if (not student_id or student_id in ("default_student", "demo", "demo_student")) else student_id
    if not course_id:
        return {"recommendations": [], "count": 0}
    ensure_course_access(db.get_by_id("courses", course_id), target_id)
    return bkt_engine.generate_recommendations(target_id, course_id)

@router.post("/learner/update")
def update_learner_state(
    request: Request,
    concept_id: str = "",
    is_correct: bool = False,
    student_id: str = "default_student",
    course_id: str = "",
    difficulty: str = "Medium"
):
    effective_id = get_student_id_from_request(request)
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    ensure_course_access(db.get_by_id("courses", course_id), effective_id)
    concept = db.get_by_id("concepts", concept_id)
    if not concept or concept.get("course_id") != course_id:
        raise HTTPException(status_code=404, detail="Concept not found")
    result = bkt_engine.update_mastery(
        student_id=effective_id,
        course_id=course_id,
        concept_id=concept_id,
        is_correct=is_correct,
        difficulty=difficulty,
        source="tutor_check"
    )
    return result

@router.post("/learner/intake")
def calibrate_new_student_intake(payload: Dict[str, Any], request: Request):
    """
    Hackathon Requirement 4b: Handle new students with no history via intake conversation / diagnostic test.
    """
    effective_id = get_student_id_from_request(request)
    course_id = payload.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    ensure_course_access(db.get_by_id("courses", course_id), effective_id)

    res = bkt_engine.calibrate_from_intake(
        student_id=effective_id,
        course_id=course_id,
        familiar_concepts=payload.get("familiar_concepts", []),
        experience_level=payload.get("experience_level", "Beginner"),
        diagnostic_score_pct=payload.get("diagnostic_score_pct"),
        notes=payload.get("notes", "")
    )
    return res

@router.post("/learner/calibrate-prior-knowledge")
def calibrate_prior_knowledge_alias(payload: Dict[str, Any], request: Request):
    return calibrate_new_student_intake(payload, request)

@router.get("/learner/{student_id}/flashcards/due")
def get_due_flashcards(student_id: str, request: Request, course_id: Optional[str] = None):
    effective_id = get_student_id_from_request(request)
    if student_id != effective_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's flashcards")
    now_iso = datetime.utcnow().isoformat()
    if course_id:
        ensure_course_access(db.get_by_id("courses", course_id), effective_id)
        mastery_recs = db.list_all("learner_mastery", lambda m: m.get("student_id") == effective_id and m.get("course_id") == course_id)
    else:
        mastery_recs = db.list_all("learner_mastery", lambda m: m.get("student_id") == effective_id)

    mastery_recs.sort(key=lambda m: m.get("next_review_date") or m.get("created_at") or "")
    due_items = [m for m in mastery_recs if (m.get("next_review_date") or "") <= now_iso]
    return {
        "student_id": effective_id,
        "course_id": course_id,
        "due_count": len(due_items),
        "cards_due": due_items,
        "all_cards": mastery_recs,
        "flashcards": due_items
    }

from backend.app.learner.rootcause import root_cause_tracer

# Cache for generated diagnoses in memory: diag_id -> diagnosis_dict
DIAGNOSES_CACHE: Dict[str, Dict[str, Any]] = {}

@router.post("/learner/diagnose-stuck")
def diagnose_stuck_endpoint(payload: Dict[str, Any], request: Request):
    """
    Part 1 Unique Feature: "Why Am I Stuck?" Root-Cause Prerequisite Tracing.
    Traverses the prerequisite DAG to locate failing foundational concepts and builds a repair path.
    """
    student_id = get_student_id_from_request(request)
    course_id = payload.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    ensure_course_access(db.get_by_id("courses", course_id), student_id)

    concept_id = payload.get("concept_id")
    assessment_id = payload.get("assessment_id")

    try:
        diagnosis = root_cause_tracer.diagnose_stuck(
            student_id=student_id,
            course_id=course_id,
            target_concept_id=concept_id,
            assessment_id=assessment_id
        )
        DIAGNOSES_CACHE[diagnosis["id"]] = diagnosis
        return diagnosis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to diagnose root cause: {str(e)}")

@router.get("/learner/{diagnosis_id}/repair-path")
def get_repair_path_endpoint(diagnosis_id: str, request: Request):
    """
    Retrieves the generated repair path and micro-diagnostic questions for a specific diagnosis.
    """
    student_id = get_student_id_from_request(request)
    diag = DIAGNOSES_CACHE.get(diagnosis_id)
    if not diag:
        raise HTTPException(status_code=404, detail="Diagnosis record not found")
    if diag.get("student_id") != student_id and diag.get("student_id") not in ("default_student", "demo", "demo_student"):
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's repair path")
    return diag

@router.get("/learner/{student_id}/misconceptions")
def get_student_misconceptions(student_id: str, request: Request, course_id: Optional[str] = None):
    effective_id = get_student_id_from_request(request)
    if student_id != effective_id and student_id not in ("default_student", "demo", "demo_student"):
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access another user's misconceptions")
    
    cond = lambda m: m.get("student_id") == effective_id
    if course_id:
        ensure_course_access(db.get_by_id("courses", course_id), effective_id)
        cond = lambda m: m.get("student_id") == effective_id and m.get("course_id") == course_id
    
    misc_list = db.list_all("misconceptions", cond)
    confident_wrong_count = sum(1 for m in misc_list if m.get("is_confident_wrong"))
    
    return {
        "student_id": effective_id,
        "course_id": course_id,
        "total_misconceptions": len(misc_list),
        "confident_wrong_count": confident_wrong_count,
        "misconceptions": misc_list
    }





