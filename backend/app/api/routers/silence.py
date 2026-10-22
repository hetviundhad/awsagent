"""
Silence Engine API Endpoints
============================
POST /silence/start              - Initialize live scratchpad session, build Misconception Atlas via Bedrock
POST /silence/tick               - Single tick update (scratchpad text + keystroke meta)
POST /silence/feedback           - Helpful / Interrupted feedback (updates adaptive thresholds)
POST /silence/patience           - Update patience dial [0.0 - 1.0]
GET  /silence/replay/{session_id} - Retrieve complete tick timeline for Time Machine scrubber
GET  /silence/stats/{session_id}  - Live counters (watched ticks, spoken count, zero tokens saved)
POST /silence/baseline/{session_id} - Replay exact session through Always-Talk baseline (Duel mode)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.api.dependencies import get_student_id_from_request
from backend.app.silence.baseline import run_always_talk_baseline
from backend.app.silence.session import get_silence_manager

router = APIRouter()


class StartSessionRequest(BaseModel):
    problem: str
    course_id: Optional[str] = "demo_course"
    course_name: Optional[str] = "Computer Science"
    topics: Optional[List[str]] = []
    weak_concepts: Optional[List[str]] = []


class TickRequest(BaseModel):
    session_id: str
    text: str
    keystroke_meta: Optional[Dict[str, Any]] = None


class FeedbackRequest(BaseModel):
    session_id: str
    helpful: bool
    rung: Optional[Any] = 2


class PatienceRequest(BaseModel):
    session_id: str
    patience: float  # 0.0 to 1.0


@router.post("/silence/start")
def silence_start(payload: StartSessionRequest, request: Request):
    try:
        student_id = get_student_id_from_request(request)
    except Exception:
        student_id = "demo_student"

    mgr = get_silence_manager()
    res = mgr.start_session(
        problem=payload.problem,
        student_id=student_id,
        course_id=payload.course_id or "demo_course",
        course_name=payload.course_name or "Computer Science",
        topics=payload.topics or [],
        weak_concepts=payload.weak_concepts or [],
    )
    return res


@router.post("/silence/tick")
def silence_tick(payload: TickRequest, request: Request):
    mgr = get_silence_manager()
    res = mgr.tick(
        session_id=payload.session_id,
        text=payload.text,
        meta_dict=payload.keystroke_meta,
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/silence/feedback")
def silence_feedback(payload: FeedbackRequest, request: Request):
    mgr = get_silence_manager()
    res = mgr.record_feedback(
        session_id=payload.session_id,
        helpful=payload.helpful,
        rung=payload.rung,
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/silence/patience")
def silence_patience(payload: PatienceRequest, request: Request):
    mgr = get_silence_manager()
    res = mgr.set_patience(
        session_id=payload.session_id,
        dial_value=payload.patience,
    )
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.get("/silence/replay/{session_id}")
def silence_replay(session_id: str):
    mgr = get_silence_manager()
    sess = mgr.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    record = sess.to_record()
    return record.to_dict()


@router.get("/silence/stats/{session_id}")
def silence_stats(session_id: str):
    mgr = get_silence_manager()
    stats = mgr.get_stats(session_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    return stats


@router.post("/silence/baseline/{session_id}")
def silence_baseline(session_id: str):
    mgr = get_silence_manager()
    sess = mgr.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    res = run_always_talk_baseline(sess.to_record())
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res
