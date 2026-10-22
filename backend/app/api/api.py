"""
backend/app/api/api.py
Unified API Router aggregating modular sub-routers:
- courses (Course lifecycle, DAG concepts, and concept map)
- materials (Document upload, streaming ingestion, user files)
- tutor (Interactive grounded tutoring, conversational memory, citations)
- assessments (Quiz generation, submission grading, misconception diagnostic)
- learner (BKT mastery tracking, study recommendations, spaced repetition flashcards)
- study (Active revision center and personalized study plans)
- evaluation (Benchmark execution, quantitative metrics, synthetic student simulation)
- settings (Config, LLM connection testing, sample loader)
- tools (AI Summarizer, Homework Solver, Material Quiz, Course Creator)
"""

from fastapi import APIRouter, Depends
from backend.app.api.dependencies import (
    get_student_id_from_request,
    get_owner_id_from_request,
    ensure_course_access,
    DEMO_STUDENT_IDS
)
from backend.app.api.routers import (
    courses,
    materials,
    tutor,
    assessments,
    learner,
    study,
    evaluation,
    settings,
    tools,
    decider,
    silence
)

# Root API router
api_router = APIRouter(prefix="/api")

# Mount modular routers
api_router.include_router(courses.router, tags=["Courses"])
api_router.include_router(materials.router, tags=["Materials"])
api_router.include_router(tutor.router, tags=["Tutor"])
api_router.include_router(assessments.router, tags=["Assessments"])
api_router.include_router(learner.router, tags=["Learner"])
api_router.include_router(study.router, tags=["Study"])
api_router.include_router(evaluation.router, tags=["Evaluation"])
api_router.include_router(settings.router, tags=["Settings"])
api_router.include_router(tools.router, tags=["Tools"])
api_router.include_router(decider.router, tags=["Decider"])
api_router.include_router(silence.router, tags=["Silence Engine"])
