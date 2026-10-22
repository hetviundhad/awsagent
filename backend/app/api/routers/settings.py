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

# --- Settings & Supabase Status ---
@router.get("/settings")
def get_system_settings():
    return {
        "environment": settings.ENVIRONMENT,
        "supabase_connected": db.is_supabase_active(),
        "supabase_url": settings.SUPABASE_URL or "",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL or "",
        "groq_configured": bool(settings.GROQ_API_KEY),
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "custom_api_base": settings.CUSTOM_API_BASE or "",
        "ollama_url": settings.OLLAMA_URL or "http://localhost:11434",
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "vision_provider": settings.VISION_PROVIDER,
        "stt_provider": settings.STT_PROVIDER,
        "confidence_threshold": settings.RETRIEVAL_CONFIDENCE_THRESHOLD,
        "demo_course_id": DEMO_COURSE_ID
    }

@router.post("/settings")
def update_settings(payload: Dict[str, Any]):
    if "supabase_url" in payload and payload["supabase_url"]:
        settings.SUPABASE_URL = payload["supabase_url"]
    if "supabase_key" in payload and payload["supabase_key"]:
        settings.SUPABASE_KEY = payload["supabase_key"]
    if "confidence_threshold" in payload:
        settings.RETRIEVAL_CONFIDENCE_THRESHOLD = float(payload["confidence_threshold"])
    if "llm_provider" in payload:
        settings.LLM_PROVIDER = payload["llm_provider"]
    if "llm_model" in payload:
        settings.LLM_MODEL = payload["llm_model"]
    if "gemini_api_key" in payload and payload["gemini_api_key"]:
        settings.GEMINI_API_KEY = payload["gemini_api_key"]
    if "groq_api_key" in payload and payload["groq_api_key"]:
        settings.GROQ_API_KEY = payload["groq_api_key"]
    if "openai_api_key" in payload and payload["openai_api_key"]:
        settings.OPENAI_API_KEY = payload["openai_api_key"]
    if "custom_api_base" in payload:
        settings.CUSTOM_API_BASE = payload["custom_api_base"]
    if "custom_api_key" in payload:
        settings.CUSTOM_API_KEY = payload["custom_api_key"]
    if "ollama_url" in payload:
        settings.OLLAMA_URL = payload["ollama_url"]
    
    # Re-init db connection
    db.init_db()
    return {
        "message": "Settings updated",
        "supabase_connected": db.is_supabase_active(),
        "active_provider": settings.LLM_PROVIDER
    }

@router.post("/settings/test-llm")
def test_llm_connection(payload: Dict[str, Any]):
    provider = payload.get("llm_provider", settings.LLM_PROVIDER)
    api_key = payload.get("api_key")
    model = payload.get("llm_model")
    base_url = payload.get("base_url")

    try:
        llm = get_llm_provider(
            provider_type=provider,
            api_key=api_key,
            model=model,
            base_url=base_url
        )
        test_res = llm.generate_grounded_tutor_response(
            query="Hello! Please confirm connection in 1 short motivating sentence.",
            retrieved_contexts=[],
            conversation_history=[],
            mode="Quick Explanation",
            difficulty="Medium",
            language="en",
            allow_outside_knowledge=True
        )
        return {
            "status": "success",
            "provider": provider,
            "response": test_res.get("answer", "Connected successfully!")
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": provider,
            "error": str(e)
        }

@router.post("/courses/sample")
def load_sample_course_endpoint(request: Request):
    """
    Load optional sample course fixture from eval/fixtures/sample_course.json
    labelled 'Sample data', isolated to the requesting user.
    """
    student_id = get_student_id_from_request(request)
    course = load_sample_course_for_user(student_id)
    return {
        "message": "Sample course loaded from eval/fixtures/ (Sample data).",
        "course": course
    }




