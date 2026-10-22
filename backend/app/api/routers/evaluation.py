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
DEMO_COURSE_ID = "sample-algorithms-course-2026"

# --- Evaluation Dashboard ---
@router.post("/evaluation/run")
def run_evaluation(payload: EvaluationRunRequest, request: Request):
    student_id = get_student_id_from_request(request)
    if not payload.course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    c_id = payload.course_id
    ensure_course_access(db.get_by_id("courses", c_id), student_id)
    results = evaluation_suite.run_rag_evaluation(c_id)
    return results

@router.get("/evaluation/results")
def get_evaluation_results():
    results = db.list_all("evaluation_results")
    if not results:
        # Return pending indicator as required by Hackathon rules
        return {
            "status": "pending",
            "message": "Evaluation pending. Click 'Run Live Benchmark' to execute real retrieval, citation, and simulation tests.",
            "metrics": None
        }
    return {
        "status": "completed",
        "metrics": results[-1]
    }

# --- Phase 5 Benchmark Export Endpoints ---
@router.get("/evaluation/export/json")
def export_evaluation_json():
    results = db.list_all("evaluation_results")
    if not results:
        courses = db.list_all("courses")
        c_id = courses[0]["id"] if courses else DEMO_COURSE_ID
        results = [evaluation_suite.run_rag_evaluation(c_id)]
    return results[-1]

# --- Phase 5 Benchmark Export Endpoints ---
@router.get("/evaluation/export/csv")
def export_evaluation_csv():
    results = db.list_all("evaluation_results")
    if not results:
        courses = db.list_all("courses")
        c_id = courses[0]["id"] if courses else DEMO_COURSE_ID
        summary = evaluation_suite.run_rag_evaluation(c_id)
    else:
        summary = results[-1]
    csv_content = evaluation_suite.export_csv(summary)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=studymind_benchmark_results.csv"}
    )

# --- Phase 4 Evaluator Agent Simulation ---
@router.post("/evaluation/simulate")
def run_student_simulation(request: Request, course_id: Optional[str] = None):
    """
    Executes a 10-session multi-agent simulation for 3 student personas.
    """
    student_id = get_student_id_from_request(request)
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    c_id = course_id
    ensure_course_access(db.get_by_id("courses", c_id), student_id)
    return synthetic_simulator.run_simulation(c_id)

@router.get("/evaluation/simulator-stream")
def stream_student_simulation(request: Request, course_id: Optional[str] = None):
    """
    SSE stream yielding live session-by-session progress for Fast Learner,
    Struggles with Math, and Skips Lectures over 10 study sessions.
    """
    student_id = get_student_id_from_request(request)
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")
    c_id = course_id
    ensure_course_access(db.get_by_id("courses", c_id), student_id)
    return StreamingResponse(
        synthetic_simulator.stream_simulation(c_id),
        media_type="text/event-stream"
    )


