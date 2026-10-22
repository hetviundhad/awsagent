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

# --- Revision Center ---
@router.get("/revision/{course_id}")
def get_revision_material(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    materials = db.list_all("revision_materials", lambda r: r.get("course_id") == course_id and r.get("student_id") == student_id)
    return materials[0] if materials else None

@router.post("/revision/{course_id}/generate")
def generate_revision_pack(course_id: str, request: Request, topic_name: Optional[str] = None):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    recommendations = bkt_engine.generate_recommendations(student_id, course_id)
    selected = next((r for r in recommendations if not topic_name or r["concept_name"].lower() == topic_name.lower()), None)
    if not selected:
        raise HTTPException(status_code=404, detail="No weak unlocked concepts need revision yet")
    topic_name = selected["concept_name"]
    grounded = rag_engine.answer_query(
        course_id=course_id,
        query=f"Create a concise revision summary, key definitions, common mistakes, formulas, and flashcards for {topic_name}. Use only uploaded course materials.",
        difficulty="Medium",
        mode="Exam Preparation",
        allow_outside_knowledge=False,
        owner_id=student_id
    )
    pack = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "course_id": course_id,
        "title": f"Revision: {topic_name}",
        "topic_name": topic_name,
        "summary": grounded.get("answer", "The uploaded course material does not cover this topic."),
        "citations": grounded.get("citations", []),
        "key_definitions": [],
        "key_formulas": [],
        "common_mistakes": [],
        "flashcards": []
    }
    db.insert("revision_materials", pack)
    return pack

# --- Study Plan ---
@router.get("/study-plan/{course_id}")
def get_study_plan(course_id: str, request: Request):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", course_id), student_id)
    plans = db.list_all("study_plans", lambda p: p.get("course_id") == course_id and p.get("student_id") == student_id)
    if plans:
        plans.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return plans[0]
    return None

@router.post("/study-plan/{course_id}/generate")
def generate_study_plan(course_id: str, request: Request, exam_date: Optional[str] = None, daily_minutes: int = 60):
    from datetime import date, timedelta, datetime
    student_id = get_student_id_from_request(request)
    course = ensure_course_access(db.get_by_id("courses", course_id), student_id)
    exam_date = exam_date or course.get("exam_date")
    if not exam_date:
        raise HTTPException(status_code=400, detail="Set an exam date for this course to generate a study plan")

    start_date = date.today()
    try:
        end_date = date.fromisoformat(exam_date[:10])
    except Exception:
        end_date = start_date + timedelta(days=14)

    if end_date < start_date:
        end_date = start_date + timedelta(days=7)

    total_days = max(1, (end_date - start_date).days + 1)

    # 1. Fetch prerequisite-aware recommendations (all available, not truncated to 4)
    recommendations = bkt_engine.generate_recommendations(student_id, course_id, limit=None) or []

    # 2. Fetch all concepts in the course
    course_concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
    concepts_by_id = {c["id"]: c for c in course_concepts}

    if not recommendations and not course_concepts:
        raise HTTPException(status_code=404, detail="No concepts available to generate a study plan")

    # 3. Identify concept overdue for spaced review (forgetting curve decay)
    mastery_list = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("course_id") == course_id)
    overdue_concept_name = None
    max_days_overdue = -1
    for m in mastery_list:
        lr = m.get("last_review")
        if lr:
            try:
                days_diff = (start_date - datetime.fromisoformat(lr[:10]).date()).days
                if days_diff > max_days_overdue:
                    max_days_overdue = days_diff
                    c = concepts_by_id.get(m.get("concept_id"))
                    if c:
                        overdue_concept_name = c.get("name")
            except Exception:
                pass

    if not overdue_concept_name and recommendations:
        overdue_concept_name = recommendations[0].get("concept_name")

    # 4. Prepare curriculum pool: prerequisites & weak topics first, then remaining concepts
    used_concept_names = set()
    topic_pool = []

    for rec in recommendations:
        topic_pool.append({
            "topic": rec["concept_name"],
            "focus": rec["reason"],
            "urgency": "High" if rec.get("recommendation_type") == "Prerequisite Foundation First" else "Normal",
            "type": "recommendation"
        })
        used_concept_names.add(rec["concept_name"])

    for c in course_concepts:
        if c.get("name") not in used_concept_names:
            topic_pool.append({
                "topic": c["name"],
                "focus": f"Advanced mastery drill and problem solving for '{c['name']}'.",
                "urgency": "Normal",
                "type": "course_concept"
            })
            used_concept_names.add(c.get("name"))

    schedule = []
    pool_idx = 0

    for day_offset in range(total_days):
        study_day = start_date + timedelta(days=day_offset)
        is_exam_day = (day_offset == total_days - 1)
        is_penultimate_day = (day_offset == total_days - 2 and total_days >= 3)
        is_consolidation_day = (day_offset > 0 and day_offset % 5 == 0 and not is_exam_day and not is_penultimate_day and len(schedule) >= 3)

        if is_exam_day:
            schedule.append({
                "date": study_day.isoformat(),
                "topic": "Comprehensive Mock Exam & High-Yield Strategy",
                "duration_min": daily_minutes,
                "focus": f"Timed simulation exam across all course modules, formula memorization check, and final score calibration. ({daily_minutes} mins intensive prep)",
                "urgency": "Highest"
            })
        elif is_penultimate_day:
            schedule.append({
                "date": study_day.isoformat(),
                "topic": "Full Course Synthesis & Rapid Retrieval",
                "duration_min": daily_minutes,
                "focus": f"Interleaved cross-module problem sets, edge cases, and high-yield flashcard drills. ({daily_minutes} mins)",
                "urgency": "High"
            })
        elif is_consolidation_day:
            prior_topic = schedule[day_offset - 3]["topic"]
            schedule.append({
                "date": study_day.isoformat(),
                "topic": f"Spaced Review & Retention: {prior_topic}",
                "duration_min": daily_minutes,
                "focus": f"Ebbinghaus forgetting curve reinforcement for '{prior_topic}'. Re-attempting past tricky questions to consolidate long-term memory.",
                "urgency": "High"
            })
        else:
            if pool_idx < len(topic_pool):
                item = topic_pool[pool_idx]
                pool_idx += 1
            else:
                item = topic_pool[pool_idx % max(1, len(topic_pool))]
                pool_idx += 1

            focus_text = item["focus"]
            if daily_minutes >= 120:
                focus_text += f" ({daily_minutes // 2}m theory & concept review + {daily_minutes - (daily_minutes // 2)}m active problem practice)."

            schedule.append({
                "date": study_day.isoformat(),
                "topic": item["topic"],
                "duration_min": daily_minutes,
                "focus": focus_text,
                "urgency": item["urgency"]
            })

    # Clean up previous plans for this course & student to avoid stale cache returns
    existing_plans = db.list_all("study_plans", lambda p: p.get("course_id") == course_id and p.get("student_id") == student_id)
    for ep in existing_plans:
        db.delete("study_plans", ep["id"])

    plan = {
        "id": str(uuid.uuid4()),
        "student_id": student_id,
        "course_id": course_id,
        "exam_date": end_date.isoformat(),
        "daily_study_minutes": daily_minutes,
        "spaced_review_alert": f"Memory retention decay detected for '{overdue_concept_name}'. Recommended active recall drill today to consolidate long-term memory." if overdue_concept_name else None,
        "schedule": schedule,
        "created_at": datetime.utcnow().isoformat()
    }
    db.insert("study_plans", plan)
    return plan


