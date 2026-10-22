"""
Glue between the pure decision layer and StudyMind's data (courses, topics, BKT learner model, chat history).
All app imports are lazy so the rest of the package stays importable (and testable) on its own.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .compose import compose
from .context import context_scores_var, route_var
from .gate import CourseProfile, GateResult, LearnerSnapshot, StudyGate, get_gate


class DeciderService:
    def __init__(self, gate: Optional[StudyGate] = None) -> None:
        self._gate = gate

    @property
    def gate(self) -> StudyGate:
        return self._gate or get_gate()

    # ------------------------------------------------------------------ data
    def course_profile(self, course_id: str) -> CourseProfile:
        from backend.app.services.database import db
        course = db.get_by_id("courses", course_id) or {}
        topics = db.list_all("topics", lambda t: t.get("course_id") == course_id) or []
        return CourseProfile(name=course.get("name", "this course"), topics=[t.get("name", "") for t in topics if t.get("name")])

    def learner_snapshot(self, student_id: str, course_id: str, learning_state: Optional[Dict[str, Any]] = None) -> LearnerSnapshot:
        try:
            if learning_state is None:
                from backend.app.learner.bkt import bkt_engine
                learning_state = bkt_engine.get_learner_profile(student_id, course_id)
            rows = learning_state.get("mastery_by_concept", [])
            return LearnerSnapshot(
                weak=[m["concept_name"] for m in rows if m.get("mastery_probability", 1) < 0.45 and not m.get("is_locked")][:8],
                mastered=[m["concept_name"] for m in rows if m.get("mastery_probability", 0) >= 0.75][:8],
                locked=[m["concept_name"] for m in rows if m.get("is_locked")][:6])
        except Exception:  # noqa: BLE001
            return LearnerSnapshot()

    def history(self, conversation_id: Optional[str]) -> Tuple[List[str], List[Dict[str, Any]]]:
        """(student-only messages for the Decider, full recent turns for Bedrock)"""
        if not conversation_id:
            return [], []
        try:
            from backend.app.services.database import db
            msgs = sorted(db.list_all("messages", lambda m: m.get("conversation_id") == conversation_id),
                          key=lambda m: m.get("created_at", ""))[-6:]
            return ([m.get("content", "") for m in msgs if m.get("role") == "user"],
                    [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in msgs])
        except Exception:  # noqa: BLE001
            return [], []

    # ------------------------------------------------------------------ gate
    def evaluate(self, *, message: str, course_id: str, student_id: str, conversation_id: Optional[str] = None,
                 learning_state: Optional[Dict[str, Any]] = None, record: bool = True) -> GateResult:
        course = self.course_profile(course_id)
        learner = self.learner_snapshot(student_id, course_id, learning_state)
        student_hist, _ = self.history(conversation_id)
        res = self.gate.evaluate(message=message, course=course, learner=learner, student_history=student_hist,
                                 student_id=student_id, course_id=course_id, record=record)
        route_var.set(res.route)              # the Bedrock provider reads this for tier/model selection
        return res

    def short_circuit_response(self, res: GateResult, message: str, course_id: str,
                               conversation_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """For clarify / redirect / support the normal RAG answer is NOT run; Bedrock writes a short reply instead."""
        if res.action not in ("clarify", "redirect", "support"):
            return None
        course = self.course_profile(course_id)
        _, turns = self.history(conversation_id)
        out = compose(res.action, message, course.name, course.topics, turns)
        topics = course.topics[:3] or [course.name]
        follow = {"clarify": [f"Explain {t}" for t in topics],
                  "redirect": [f"Explain {topics[0]}", f"Quiz me on {course.name}", "What topics are covered in my course material?"],
                  "support": ["Give me a 10-minute study plan", "Quiz me gently on something I know", f"Explain {topics[0]} simply"]}[res.action]
        return {
            "answer": out["text"],
            "answer_segments": [{"text": out["text"], "citations": [], "type": "outside"}],
            "grounded": True, "is_outside_knowledge": False, "refused": False, "citations": [],
            "external_links": [], "confidence_score": 1.0, "searched_topics": [],
            "closest_source": None, "conversation_id": conversation_id or "new_conv",
            "follow_up_questions": follow, "verification_check_question": None,
            "generated_by": out["generated_by"], "gate_action": res.action,
        }

    # ------------------------------------------------------------------ RAG hook
    def filter_context(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chunks or _disabled("DECIDER_CONTEXT_SCORING"):
            return chunks
        out = self.gate.score_context(query, chunks)
        store = context_scores_var.get()
        if store is not None:
            store["scores"] = [{"chunk_id": c.get("id"), "document": c.get("document_name"),
                                "relevance": c.get("decider_relevance")} for c in out if c.get("decider_relevance") is not None]
            store["dropped"] = max(0, len(chunks) - len(out))
        return out

    # ------------------------------------------------------------------ feedback
    def feedback(self, trace_id: str, helpful: bool) -> Dict[str, Any]:
        tr = self.gate.traces.get(trace_id)
        if not tr:
            return {"ok": False, "error": "trace not found"}
        changes = []
        for d in tr.get("decisions", []):
            r = self.gate.thresholds.feedback(
                {"threshold_key": d.get("threshold_key"), "triggered": d.get("triggered"),
                 "measure": d.get("measure"), "fallback": d.get("fallback")}, helpful)
            if r.get("changed"):
                changes.append(r)
        self.gate.traces.update(trace_id, feedback="up" if helpful else "down")
        return {"ok": True, "threshold_changes": changes, "thresholds": self.gate.thresholds.snapshot()}

    def status(self) -> Dict[str, Any]:
        from backend.app.providers.bedrock_provider import get_bedrock
        client = self.gate.client
        h = client.health()
        br = get_bedrock()
        st = client.stats
        mc = st["model_calls"]
        return {
            "decider": {**h, "url": client.url, "breaker_open": client.breaker_open,
                        "allow_fallback": client.allow_fallback, "calls": st["calls"], "model_calls": mc,
                        "fallback_calls": st["fallback_calls"], "errors": st["errors"],
                        "avg_model_ms": round(st["total_model_latency_ms"] / mc, 1) if mc else None},
            "bedrock": {**br.status(force=True), "calls": br.stats["calls"],
                        "avg_ms": round(br.stats["total_ms"] / br.stats["calls"], 1) if br.stats["calls"] else None},
            "thresholds": self.gate.thresholds.snapshot(),
            "traces": self.gate.traces.summary(),
        }


def _disabled(env: str) -> bool:
    import os
    return os.environ.get(env, "true").lower() in ("0", "false", "no")


decider_service = DeciderService()
