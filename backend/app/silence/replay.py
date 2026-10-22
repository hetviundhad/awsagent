"""
Replay and timeline storage for the Silence Engine.
Stores the complete, chronological tick record for Time Machine scrubbing and head-to-head benchmarking.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _storage_dir() -> str:
    base = os.environ.get("STORAGE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "data",
        "storage",
    )
    d = os.path.join(base, "silence_sessions")
    os.makedirs(d, exist_ok=True)
    return d


@dataclass
class TickRecord:
    tick_index: int
    timestamp: float
    scratchpad: str
    diff: str
    probabilities: Dict[str, float]
    rung: Any
    rung_name: str
    token_class: str
    held_back_by: Optional[str]
    action_type: str
    spoken: bool
    spoken_text: Optional[str]
    spoken_target_line: Optional[int]
    decider_mode: str
    decider_ms: float
    llm_tokens: int = 0


@dataclass
class SessionRecord:
    session_id: str
    student_id: str
    course_id: str
    problem: str
    course_name: str
    atlas_summary: Dict[str, Any]
    created_at: float
    patience_dial: float = 0.5
    ticks: List[TickRecord] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "problem": self.problem,
            "course_name": self.course_name,
            "atlas_summary": self.atlas_summary,
            "created_at": self.created_at,
            "patience_dial": self.patience_dial,
            "stats": self.stats,
            "ticks": [asdict(t) for t in self.ticks],
        }


class ReplayStore:
    def __init__(self, directory: Optional[str] = None) -> None:
        self.directory = directory or _storage_dir()
        self._lock = threading.Lock()
        self._memory_cache: Dict[str, SessionRecord] = {}

    def _file_path(self, session_id: str) -> str:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.directory, f"{safe_id}.json")

    def save_session(self, record: SessionRecord) -> None:
        with self._lock:
            self._memory_cache[record.session_id] = record
            try:
                path = self._file_path(record.session_id)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(record.to_dict(), f, indent=2)
                os.replace(tmp, path)
            except OSError as exc:
                print(f"[silence.replay] Failed to persist session {record.session_id}: {exc}")

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        with self._lock:
            if session_id in self._memory_cache:
                return self._memory_cache[session_id]
            path = self._file_path(session_id)
            if not os.path.exists(path):
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ticks = [TickRecord(**t) for t in data.get("ticks", [])]
                record = SessionRecord(
                    session_id=data["session_id"],
                    student_id=data.get("student_id", ""),
                    course_id=data.get("course_id", ""),
                    problem=data.get("problem", ""),
                    course_name=data.get("course_name", ""),
                    atlas_summary=data.get("atlas_summary", {}),
                    created_at=data.get("created_at", time.time()),
                    patience_dial=data.get("patience_dial", 0.5),
                    ticks=ticks,
                    stats=data.get("stats", {}),
                )
                self._memory_cache[session_id] = record
                return record
            except Exception as exc:
                print(f"[silence.replay] Error loading session {session_id}: {exc}")
                return None


_replay_store: Optional[ReplayStore] = None


def get_replay_store() -> ReplayStore:
    global _replay_store
    if _replay_store is None:
        _replay_store = ReplayStore()
    return _replay_store
