"""
/api/decider/*  - the Decision Lab + audit trail for Strands Decider 2B.

  GET  /decider/status        live health of Decider server, Bedrock, thresholds, latency stats
  POST /decider/decide        run the gate on a message (optionally generate the Bedrock reply) without chatting
  GET  /decider/traces        recent decisions for this student
  POST /decider/feedback      thumbs up/down on a decision -> thresholds adapt
  GET  /decider/thresholds    current adaptive thresholds + change history
  POST /decider/thresholds/reset
  POST /decider/agent         Strands agent (Bedrock) guarded by Decider 2B (InterventionHandler)
  GET  /decider/benchmark     last benchmark written by scripts/benchmark_decider.py
"""
import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.app.api.dependencies import ensure_course_access, get_student_id_from_request
from backend.app.core.config import settings
from backend.app.decider.service import decider_service
from backend.app.services.database import db

router = APIRouter()


class DecideRequest(BaseModel):
    course_id: str
    message: str
    conversation_id: Optional[str] = None
    generate: bool = False          # also have Bedrock write the clarify/redirect/support reply


class FeedbackRequest(BaseModel):
    trace_id: str
    helpful: bool


class AgentRequest(BaseModel):
    course_id: str
    message: str


@router.get("/decider/status")
def decider_status():
    return decider_service.status()


@router.post("/decider/decide")
def decider_decide(payload: DecideRequest, request: Request):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", payload.course_id), student_id)
    res = decider_service.evaluate(message=payload.message, course_id=payload.course_id, student_id=student_id,
                                   conversation_id=payload.conversation_id)
    out = res.to_public()
    if payload.generate:
        sc = decider_service.short_circuit_response(res, payload.message, payload.course_id, payload.conversation_id)
        out["generated"] = sc
    return out


@router.get("/decider/traces")
def decider_traces(request: Request, limit: int = 30):
    student_id = get_student_id_from_request(request)
    return {"traces": decider_service.gate.traces.recent(student_id, min(max(limit, 1), 100)),
            "summary": decider_service.gate.traces.summary()}


@router.post("/decider/feedback")
def decider_feedback(payload: FeedbackRequest, request: Request):
    get_student_id_from_request(request)
    res = decider_service.feedback(payload.trace_id, payload.helpful)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error", "trace not found"))
    return res


@router.get("/decider/thresholds")
def decider_thresholds():
    return decider_service.gate.thresholds.snapshot()


@router.post("/decider/thresholds/reset")
def decider_thresholds_reset(request: Request):
    get_student_id_from_request(request)
    decider_service.gate.thresholds.reset()
    return decider_service.gate.thresholds.snapshot()


@router.post("/decider/agent")
def decider_agent(payload: AgentRequest, request: Request):
    student_id = get_student_id_from_request(request)
    ensure_course_access(db.get_by_id("courses", payload.course_id), student_id)
    from backend.app.decider.strands_agent import STRANDS_AVAILABLE, run_agent
    from backend.app.providers.bedrock_provider import get_bedrock
    if not STRANDS_AVAILABLE:
        raise HTTPException(status_code=501, detail="strands-agents is not installed. pip install strands-agents 'botocore[crt]'")
    st = get_bedrock().status(force=True)
    if not st["ok"]:
        raise HTTPException(status_code=503, detail=f"Amazon Bedrock not available: {st['error']}")
    try:
        return run_agent(payload.course_id, student_id, payload.message)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}")


@router.get("/decider/benchmark")
def decider_benchmark():
    path = os.path.join(settings.STORAGE_DIR, "decider_benchmark.json")
    if not os.path.exists(path):
        return {"available": False, "hint": "run: python scripts/benchmark_decider.py"}
    with open(path, "r", encoding="utf-8") as f:
        return {"available": True, **json.load(f)}
