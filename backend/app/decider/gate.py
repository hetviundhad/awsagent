"""
StudyGate - ONE Decider round trip per student message.

    policy      (choice)  what does the student need?            -> answer | quiz | socratic | support | redirect
    clarity     (noul)    is the message specific enough?         -> clarify instead of guessing
    complexity  (noul)    does it need a deep model?              -> route to fast / deep Bedrock model
    prereq      (noul)    does it lean on a weak concept?         -> prepend a prerequisite nudge

All four questions share the same state, which the model encodes once - that is the point of a decision model.
Plain Python (below) owns the control flow; the model only supplies calibrated numbers.
Fails OPEN: if anything breaks, the tutor answers normally.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import patterns as P
from .calibration import ThresholdStore, get_thresholds
from .client import DeciderClient, get_client
from .trace import TraceStore, get_traces

CHITCHAT = {"hi", "hello", "hey", "hola", "thanks", "thank you", "thx", "ok", "okay", "bye", "cool", "nice", "great"}


@dataclass
class CourseProfile:
    name: str = "this course"
    topics: List[str] = field(default_factory=list)


@dataclass
class LearnerSnapshot:
    weak: List[str] = field(default_factory=list)
    mastered: List[str] = field(default_factory=list)
    locked: List[str] = field(default_factory=list)


@dataclass
class GateResult:
    action: str                                   # answer | quiz | socratic | support | redirect | clarify
    mode_override: Optional[str] = None           # e.g. "Socratic" for the existing provider prompts
    route: Dict[str, Any] = field(default_factory=dict)
    learner_hint: str = ""
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    decider_mode: str = "model"                   # model | fallback | unavailable | skipped
    decider_ms: float = 0.0
    trace_id: Optional[str] = None
    skipped_reason: Optional[str] = None

    def to_public(self) -> Dict[str, Any]:
        return {"trace_id": self.trace_id, "action": self.action, "route": self.route,
                "decisions": self.decisions, "decider_mode": self.decider_mode,
                "decider_ms": round(self.decider_ms, 1), "learner_hint": self.learner_hint,
                "skipped_reason": self.skipped_reason}


def _model_ids() -> Dict[str, Optional[str]]:
    return {
        "fast": os.environ.get("BEDROCK_MODEL_FAST", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
        "deep": os.environ.get("BEDROCK_MODEL_DEEP", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    }


class StudyGate:
    def __init__(self, client: Optional[DeciderClient] = None, thresholds: Optional[ThresholdStore] = None,
                 traces: Optional[TraceStore] = None) -> None:
        self.client = client or get_client()
        self.thresholds = thresholds or get_thresholds()
        self.traces = traces or get_traces()

    # ------------------------------------------------------------------ #
    def evaluate(self, *, message: str, course: CourseProfile, learner: LearnerSnapshot,
                 student_history: Sequence[str] = (), student_id: str = "", course_id: str = "",
                 record: bool = True) -> GateResult:
        msg = (message or "").strip()
        words = msg.split()
        if not msg or msg.lower().strip("!?. ") in CHITCHAT or (len(words) <= 2 and "?" not in msg):
            res = GateResult(action="answer", decider_mode="skipped", skipped_reason="chit-chat / too short to classify",
                             route=self._route(False, "chit-chat uses the fast model"))
            return self._finish(res, msg, student_id, course_id, record)

        try:
            pats: List[P.Pattern] = [P.pedagogy_policy(course.name, course.topics), P.clarity_check(),
                                     P.complexity_router()]
            prereq = P.prereq_gap(learner.weak)           # only asked when the learner model has weak concepts
            if prereq:
                pats.append(prereq)
            state = P.build_state(course=course.name, topics=course.topics, weak=learner.weak,
                                  mastered=learner.mastered, locked=learner.locked,
                                  student_history=student_history, message=msg)
            decisions, ask = P.run_patterns(self.client, state, pats, self.thresholds.get)
            if not decisions:
                res = GateResult(action="answer", decider_mode=ask.mode, skipped_reason=ask.error,
                                 route=self._route(False, "decider unavailable - default model"))
                return self._finish(res, msg, student_id, course_id, record)
            res = self._act(decisions, ask.mode, ask.latency_ms, learner, msg)
        except Exception as exc:  # noqa: BLE001  fail OPEN - the tutor must always answer
            res = GateResult(action="answer", decider_mode="unavailable", skipped_reason=f"gate error: {exc}",
                             route=self._route(False, "gate error - default model"))
        return self._finish(res, msg, student_id, course_id, record)

    # ------------------------------------------------------------------ #
    def _act(self, d: Dict[str, P.Decision], mode: str, ms: float, learner: LearnerSnapshot, msg: str) -> GateResult:
        """THE control flow. Every branch is plain Python on top of calibrated numbers."""
        policy, clarity, cx, pre = d.get("policy"), d.get("clarity"), d.get("complexity"), d.get("prereq")
        action, mode_override = "answer", None

        if policy and policy.triggered and policy.action:
            action = policy.action
            if action == "socratic":
                mode_override = "Socratic"
        # An unclear message beats everything except support/redirect (those don't need a concept).
        if clarity and clarity.triggered and action in ("answer", "socratic", "quiz"):
            action, mode_override = "clarify", None

        deep = bool(cx and cx.triggered and action in ("answer", "socratic"))
        route = self._route(deep, f"P(complex)={cx.measure:.0%}" if cx else "no routing signal")

        hint = ""
        if pre and pre.triggered and action in ("answer", "socratic"):
            hint = ("The student's question leans on a concept they are still weak in "
                    f"({', '.join(learner.weak[:3])}). Briefly revisit that prerequisite before the main answer.")
        return GateResult(action=action, mode_override=mode_override, route=route, learner_hint=hint,
                          decisions=[x.to_dict() for x in d.values()], decider_mode=mode, decider_ms=ms)

    def _route(self, deep: bool, reason: str) -> Dict[str, Any]:
        ids = _model_ids()
        tier = "deep" if deep else "fast"
        return {"tier": tier, "model_id": ids[tier], "reason": reason}

    def _finish(self, res: GateResult, msg: str, student_id: str, course_id: str, record: bool) -> GateResult:
        if record:
            t = self.traces.add({"student_id": student_id, "course_id": course_id, "message": msg[:200],
                                 "action": res.action, "route": res.route, "decisions": res.decisions,
                                 "decider_mode": res.decider_mode, "decider_ms": res.decider_ms,
                                 "skipped_reason": res.skipped_reason, "feedback": None})
            res.trace_id = t["id"]
        return res

    # ------------------------------------------------------------------ #
    def score_context(self, query: str, chunks: List[Dict[str, Any]], budget_ms: float = 2500.0,
                      max_chunks: int = 5) -> List[Dict[str, Any]]:
        """#context-memory: score each retrieved chunk BEFORE it reaches the prompt.
        Sequential on purpose (the server is best driven one request at a time) and time-boxed.
        Adds `decider_relevance` to every chunk it scored; drops chunks clearly below threshold but never all of them."""
        if len(chunks) < 2 or self.client.breaker_open:
            return chunks
        pat = P.context_relevance()
        thr = self.thresholds.get("relevance")
        t0 = time.perf_counter()
        scored: List[Dict[str, Any]] = []
        for ch in chunks[:max_chunks]:
            if (time.perf_counter() - t0) * 1000 > budget_ms:
                break
            state = f"{query.strip()[:400]}\n--- EXCERPT ---\n{str(ch.get('content', ''))[:700]}"
            dec, ask = P.run_patterns(self.client, state, [pat], self.thresholds.get)
            if ask.mode != "model" or "relevance" not in dec:
                return chunks                              # fallback numbers must never reshape real context
            ch["decider_relevance"] = round(dec["relevance"].measure, 3)
            scored.append(ch)
        if not scored:
            return chunks
        kept = [c for c in scored if c["decider_relevance"] >= thr]
        rest = chunks[len(scored):]
        return (kept or scored[:1]) + rest                 # fail-safe: never return an empty context


_gate: Optional[StudyGate] = None


def get_gate() -> StudyGate:
    global _gate
    if _gate is None:
        _gate = StudyGate()
    return _gate
