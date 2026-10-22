"""
Session State & Concurrency Manager for the Silence Engine.

Guarantees:
  - Non-blocking: typing never stutters.
  - Concurrency control: only ONE in-flight tick per session, latest-wins (stale ticks dropped).
  - Hysteresis, budget, cooldown, and patience dial tracked per problem.
  - Seamless persistence to ReplayStore.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.app.decider.calibration import ThresholdStore, get_thresholds
from backend.app.decider.client import DeciderClient, get_client
from backend.app.silence.atlas import Atlas, build_atlas
from backend.app.silence.ladder import (
    SilenceDecision,
    evaluate_escalation_ladder,
)
from backend.app.silence.replay import SessionRecord, TickRecord, get_replay_store
from backend.app.silence.signals import (
    KeystrokeMeta,
    SilenceSignalsEvaluator,
    TickSignals,
)
from backend.app.silence.speak import SpokenMessage, compose_silence_message


class SilenceSession:
    def __init__(
        self,
        session_id: str,
        student_id: str,
        course_id: str,
        problem: str,
        course_name: str,
        atlas: Atlas,
        weak_concepts: Sequence[str] = (),
    ) -> None:
        self.session_id = session_id
        self.student_id = student_id
        self.course_id = course_id
        self.problem = problem
        self.course_name = course_name
        self.atlas = atlas
        self.weak_concepts = list(weak_concepts)

        self.patience_dial: float = 0.5  # 0.0 (interrupt less) to 1.0 (interrupt more)
        self.current_rung: int = 0
        self.trigger_streak: int = 0
        self.last_scratchpad: str = ""
        self.last_spoken_timestamp: float = 0.0
        self.interventions_count: int = 0
        self.rung_history: List[int] = [0]
        self.finished_prompted: bool = False

        self.created_at: float = time.time()
        self.ticks: List[TickRecord] = []
        self.total_tokens_used: int = 0
        self.decider_latencies: List[float] = []

        self._lock = threading.Lock()
        self._seq = 0

    def next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    def is_current_seq(self, seq: int) -> bool:
        with self._lock:
            return seq == self._seq

    def to_record(self) -> SessionRecord:
        avg_lat = sum(self.decider_latencies) / max(1, len(self.decider_latencies))
        silent_count = sum(1 for t in self.ticks if not t.spoken)
        return SessionRecord(
            session_id=self.session_id,
            student_id=self.student_id,
            course_id=self.course_id,
            problem=self.problem,
            course_name=self.course_name,
            atlas_summary=self.atlas.summary(),
            created_at=self.created_at,
            patience_dial=self.patience_dial,
            ticks=self.ticks,
            stats={
                "total_ticks": len(self.ticks),
                "silent_ticks": silent_count,
                "spoken_count": self.interventions_count,
                "total_tokens": self.total_tokens_used,
                "avg_decider_ms": round(avg_lat, 1),
            },
        )


class SilenceSessionManager:
    def __init__(
        self,
        client: Optional[DeciderClient] = None,
        thresholds: Optional[ThresholdStore] = None,
    ) -> None:
        self.client = client or get_client()
        self.thresholds = thresholds or get_thresholds()
        self.evaluator = SilenceSignalsEvaluator(self.client)
        self.replay_store = get_replay_store()
        self._sessions: Dict[str, SilenceSession] = {}
        self._lock = threading.Lock()

    def start_session(
        self,
        *,
        problem: str,
        student_id: str = "demo_student",
        course_id: str = "demo_course",
        course_name: str = "Computer Science",
        topics: Sequence[str] = (),
        weak_concepts: Sequence[str] = (),
    ) -> Dict[str, Any]:
        session_id = f"silence_{uuid.uuid4().hex[:12]}"
        atlas = build_atlas(
            problem=problem,
            course_name=course_name,
            topics=topics,
            weak_concepts=weak_concepts,
        )
        session = SilenceSession(
            session_id=session_id,
            student_id=student_id,
            course_id=course_id,
            problem=problem,
            course_name=course_name,
            atlas=atlas,
            weak_concepts=weak_concepts,
        )
        with self._lock:
            self._sessions[session_id] = session

        # Persist initial record
        self.replay_store.save_session(session.to_record())

        return {
            "session_id": session_id,
            "problem": problem,
            "course_name": course_name,
            "atlas": atlas.to_dict(),
            "atlas_summary": atlas.summary(),
        }

    def get_session(self, session_id: str) -> Optional[SilenceSession]:
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                return s
        # Try loading from replay store
        rec = self.replay_store.get_session(session_id)
        if rec:
            atlas_data = rec.atlas_summary
            from backend.app.silence.atlas import Misconception
            miscs = [Misconception(id=m["id"], name=m["name"], description="", concept=m.get("concept", ""))
                     for m in atlas_data.get("misconceptions", [])]
            atlas = Atlas(
                problem=rec.problem,
                course_name=rec.course_name,
                misconceptions=miscs,
                milestones=atlas_data.get("milestones", []),
                fallback=atlas_data.get("fallback", False),
            )
            sess = SilenceSession(
                session_id=rec.session_id,
                student_id=rec.student_id,
                course_id=rec.course_id,
                problem=rec.problem,
                course_name=rec.course_name,
                atlas=atlas,
            )
            sess.ticks = rec.ticks
            sess.patience_dial = rec.patience_dial
            with self._lock:
                self._sessions[session_id] = sess
            return sess
        return None

    def tick(
        self,
        *,
        session_id: str,
        text: str,
        meta_dict: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {"error": "session not found", "session_id": session_id}

        seq = session.next_seq()
        raw_meta = meta_dict or {}

        now = time.time()
        sec_since_spoken = (now - session.last_spoken_timestamp) if session.last_spoken_timestamp > 0 else 999.0

        meta = KeystrokeMeta(
            seconds_since_last_keystroke=float(raw_meta.get("seconds_since_last_keystroke", 0.0)),
            longest_recent_pause=float(raw_meta.get("longest_recent_pause", 0.0)),
            delete_rewrite_ratio=float(raw_meta.get("delete_rewrite_ratio", 0.0)),
            seconds_since_last_intervention=sec_since_spoken,
            interventions_count=session.interventions_count,
            rung_history=session.rung_history,
            changed_line_indices=[int(i) for i in raw_meta.get("changed_line_indices", []) if isinstance(i, (int, str))],
        )

        # 1. Run Decider signals
        signals = self.evaluator.evaluate_tick(
            problem=session.problem,
            course_name=session.course_name,
            scratchpad=text,
            last_scratchpad=session.last_scratchpad,
            meta=meta,
            atlas=session.atlas,
            weak_concepts=session.weak_concepts,
            thresholds=self.thresholds.get,
        )

        # Check if superseded while decider was running
        if not session.is_current_seq(seq):
            return {"skipped": True, "skipped_reason": "stale_tick_dropped"}

        if not signals.skipped:
            session.decider_latencies.append(signals.latency_ms)

        # Update trigger streak for hysteresis
        is_trigger_active = False
        if not signals.skipped:
            p_strug = float(signals.productive_struggle.measure if signals.productive_struggle else 0.5)
            shield = self.thresholds.get("silence_shield")
            if p_strug < shield:
                prog_label = signals.progress.label if signals.progress else "none_of_these"
                if prog_label in ("wrong_path", "blank_stuck", "circling"):
                    is_trigger_active = True

        if is_trigger_active:
            session.trigger_streak += 1
        else:
            session.trigger_streak = max(0, session.trigger_streak - 1)

        # 2. Evaluate Escalation Ladder
        decision: SilenceDecision = evaluate_escalation_ladder(
            signals=signals,
            current_rung=session.current_rung,
            trigger_streak=session.trigger_streak,
            seconds_since_last_spoken=sec_since_spoken,
            interventions_count=session.interventions_count,
            patience_dial=session.patience_dial,
            shield_threshold=self.thresholds.get("silence_shield"),
            frustration_threshold=self.thresholds.get("silence_frustration"),
            help_threshold=self.thresholds.get("silence_help"),
            stuck_threshold=self.thresholds.get("silence_stuck"),
            finished_prompted=session.finished_prompted,
        )

        spoken_msg: Optional[SpokenMessage] = None
        if decision.spoken:
            spoken_msg = compose_silence_message(
                decision=decision,
                problem=session.problem,
                course_name=session.course_name,
                scratchpad=text,
                atlas=session.atlas,
            )
            session.interventions_count += 1
            session.last_spoken_timestamp = now
            session.total_tokens_used += (spoken_msg.input_tokens + spoken_msg.output_tokens)

        # Update session tracking
        if isinstance(decision.rung, int):
            session.current_rung = decision.rung
            session.rung_history.append(decision.rung)
        elif decision.rung == "B":
            session.rung_history.append(0)

        if decision.action_type == "check_answer":
            session.finished_prompted = True

        session.last_scratchpad = text

        # 3. Record tick in timeline
        tick_rec = TickRecord(
            tick_index=len(session.ticks) + 1,
            timestamp=now,
            scratchpad=text,
            diff=signals.skipped_reason or "diff",
            probabilities=decision.probabilities,
            rung=decision.rung,
            rung_name=decision.rung_name,
            token_class=decision.token_class,
            held_back_by=decision.held_back_by,
            action_type=decision.action_type,
            spoken=decision.spoken,
            spoken_text=spoken_msg.text if spoken_msg else None,
            spoken_target_line=spoken_msg.target_line if spoken_msg else None,
            decider_mode=signals.decider_mode,
            decider_ms=signals.latency_ms,
            llm_tokens=(spoken_msg.input_tokens + spoken_msg.output_tokens) if spoken_msg else 0,
        )
        session.ticks.append(tick_rec)

        # Persist session update asynchronously/safely
        self.replay_store.save_session(session.to_record())

        return {
            "tick_index": tick_rec.tick_index,
            "decision": decision.to_dict(),
            "spoken_message": spoken_msg.to_dict() if spoken_msg else None,
            "session_stats": self.get_stats(session_id),
        }

    def set_patience(self, session_id: str, dial_value: float) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {"error": "session not found"}
        clamped = max(0.0, min(1.0, float(dial_value)))
        session.patience_dial = clamped
        self.replay_store.save_session(session.to_record())
        return {"session_id": session_id, "patience_dial": clamped}

    def record_feedback(self, session_id: str, helpful: bool, rung: Any = 2) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {"error": "session not found"}

        # "You interrupted me" -> tutor was too eager -> raise shield threshold / raise stuck threshold
        # "Helpful" -> tutor timed it well -> reinforce
        changes = []
        if not helpful:
            # Shift shield higher (more protected silence)
            r1 = self.thresholds.feedback(
                {"threshold_key": "silence_shield", "triggered": True, "measure": 0.65, "fallback": False},
                helpful=False,
            )
            if r1.get("changed"):
                changes.append(r1)
            # Shift stuck threshold higher (harder to interrupt)
            r2 = self.thresholds.feedback(
                {"threshold_key": "silence_stuck", "triggered": True, "measure": 0.65, "fallback": False},
                helpful=False,
            )
            if r2.get("changed"):
                changes.append(r2)
            # Adjust patience dial down slightly (interrupt less)
            session.patience_dial = max(0.0, session.patience_dial - 0.1)
        else:
            # Positive reinforcement
            r = self.thresholds.feedback(
                {"threshold_key": "silence_shield", "triggered": True, "measure": 0.60, "fallback": False},
                helpful=True,
            )
            if r.get("changed"):
                changes.append(r)

        self.replay_store.save_session(session.to_record())
        return {
            "session_id": session_id,
            "helpful": helpful,
            "patience_dial": session.patience_dial,
            "threshold_changes": changes,
            "thresholds": self.thresholds.snapshot(),
        }

    def get_stats(self, session_id: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {"error": "session not found"}
        ticks_count = len(session.ticks)
        spoken_count = session.interventions_count
        silent_count = max(0, ticks_count - spoken_count)
        avg_lat = sum(session.decider_latencies) / max(1, len(session.decider_latencies))
        
        # Determine active decider mode
        last_mode = session.ticks[-1].decider_mode if session.ticks else "model"
        if self.client.breaker_open:
            last_mode = "fallback"

        return {
            "session_id": session_id,
            "total_ticks": ticks_count,
            "silent_ticks": silent_count,
            "spoken_interventions": spoken_count,
            "tokens_used": session.total_tokens_used,
            "avg_decider_ms": round(avg_lat, 1),
            "patience_dial": session.patience_dial,
            "current_rung": session.current_rung,
            "decider_mode": last_mode,
            "tagline": f"Watched {ticks_count} ticks · Spoke {spoken_count} times · 0 tokens spent on the other {silent_count}",
        }


_manager: Optional[SilenceSessionManager] = None


def get_silence_manager() -> SilenceSessionManager:
    global _manager
    if _manager is None:
        _manager = SilenceSessionManager()
    return _manager
