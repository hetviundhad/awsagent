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

# --- Assessments ---
@router.get("/assessments/quota")
def get_assessment_quota(request: Request):
    student_id = get_student_id_from_request(request)
    limit = getattr(settings, "FREE_QUIZ_LIMIT", None)
    used = len(db.list_all("attempts", lambda a: a.get("user_id") == student_id))
    return {
        "free_quiz_limit": limit,
        "used_quizzes": used,
        "unlimited": limit is None
    }

@router.post("/assessments/generate")
def generate_assessment(payload: AssessmentGenerateRequest, request: Request):
    student_id = get_student_id_from_request(request)
    course = db.get_by_id("courses", payload.course_id)
    ensure_course_access(course, student_id)

    # Check free quiz limit if configured
    free_limit = getattr(settings, "FREE_QUIZ_LIMIT", None)
    if free_limit is not None:
        user_attempts = db.list_all("attempts", lambda a: a.get("user_id") == student_id)
        if len(user_attempts) >= free_limit:
            raise HTTPException(status_code=403, detail=f"Free quiz quota reached ({len(user_attempts)}/{free_limit}).")

    try:
        assessment = assessment_engine.generate_assessment(
            course_id=payload.course_id,
            unit_id=payload.unit_id,
            topic_id=payload.topic_id,
            concept_id=payload.concept_id,
            concept_name=payload.concept_name,
            document_ids=payload.document_ids,
            concept_ids=payload.concept_ids,
            topic_ids=payload.topic_ids,
            question_count=payload.question_count,
            question_types=payload.question_types,
            difficulty=payload.difficulty,
            language=payload.language,
            mode=payload.mode or "standard",
            practical_ratio=payload.practical_ratio if payload.practical_ratio is not None else 0.70,
            time_limit_minutes=payload.time_limit_minutes,
            student_id=student_id
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return assessment

@router.post("/assessments/chat-quiz")
def generate_chat_quiz_endpoint(payload: Dict[str, Any], request: Request):
    student_id = get_student_id_from_request(request)
    course_id = payload.get("course_id")
    ensure_course_access(db.get_by_id("courses", course_id) if course_id else None, student_id)
    conversation_id = payload.get("conversation_id")
    question_count = int(payload.get("question_count", 3))

    quiz = assessment_engine.generate_chat_quiz(
        course_id=course_id,
        conversation_id=conversation_id,
        student_id=student_id,
        question_count=question_count
    )
    return quiz

@router.get("/assessments")
def list_assessments(request: Request, course_id: Optional[str] = None):
    student_id = get_student_id_from_request(request)
    if course_id:
        return db.list_all("assessments", lambda a: a.get("course_id") == course_id)
    return db.list_all("assessments")

@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, request: Request):
    assessment = db.get_by_id("assessments", assessment_id)
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", assessment.get("course_id")) if assessment else None, student_id)
    if not assessment.get("questions"):
        links = sorted(
            db.list_all("assessment_questions", lambda aq: aq.get("assessment_id") == assessment_id),
            key=lambda aq: aq.get("sort_order", 0)
        )
        assessment["questions"] = [q for link in links if (q := db.get_by_id("questions", link.get("question_id", "")))]
    safe_assessment = dict(assessment)
    normalized_questions = []
    for question in assessment.get("questions", []):
        q_dict = dict(question)
        txt = q_dict.get("question_text") or q_dict.get("stem") or q_dict.get("question") or "Assessment Question"
        q_dict["question_text"] = txt
        q_dict["stem"] = txt
        q_dict["question"] = txt
        if not q_dict.get("options") or not isinstance(q_dict["options"], list):
            q_dict["options"] = ["Option A", "Option B", "Option C", "Option D"]
        # Hide answer and explanation during live exam
        q_dict.pop("correct_answer", None)
        q_dict.pop("explanation", None)
        normalized_questions.append(q_dict)
    safe_assessment["questions"] = normalized_questions
    return safe_assessment

@router.post("/assessments/{assessment_id}/submit")
def submit_assessment(assessment_id: str, payload: AssessmentSubmitRequest, request: Request):
    student_id = get_student_id_from_request(request)
    assessment = db.get_by_id("assessments", assessment_id)
    ensure_course_access(db.get_by_id("courses", assessment.get("course_id")) if assessment else None, student_id)
    try:
        report = assessment_engine.evaluate_submission(
            assessment_id=assessment_id,
            student_answers=payload.student_answers,
            student_confidences=payload.student_confidences,
            time_spent_seconds=payload.time_spent_seconds,
            student_id=student_id,
            auto_submitted=payload.auto_submitted,
            safe_mode_violation=payload.safe_mode_violation
        )

        db.update("assessments", assessment_id, {"last_report": report})
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/assessments/{assessment_id}/report")
def get_assessment_report(assessment_id: str, request: Request):
    assessment = db.get_by_id("assessments", assessment_id)
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", assessment.get("course_id")) if assessment else None, student_id)
    
    if assessment.get("last_report"):
        return assessment["last_report"]

    raise HTTPException(status_code=404, detail="This assessment has not been submitted yet")


# --- Assessment Diagnostics & Misconceptions ---
@router.get("/assessment/validation-metrics")
def get_assessment_validation_metrics():
    """
    Returns real cross-model question validation metrics and discard rates.
    """
    return assessment_engine.get_validation_metrics()

@router.post("/assessment/misconception-brief")
def get_misconception_brief(payload: Dict[str, Any]):
    """
    Generates a 2-minute audio brief script and playback details for a diagnosed misconception.
    """
    misconception = payload.get("misconception", "")
    concept_name = payload.get("concept_name", "Core Concept")
    return assessment_engine.generate_misconception_brief(misconception, concept_name)

@router.post("/assessment/misconception-flashcards")
def get_misconception_flashcards(payload: Dict[str, Any]):
    """
    Generates targeted diagnostic flashcards specifically dismantling the identified misconception.
    """
    misconception = payload.get("misconception", "")
    concept_name = payload.get("concept_name", "Core Concept")
    return assessment_engine.generate_misconception_flashcards(misconception, concept_name)


