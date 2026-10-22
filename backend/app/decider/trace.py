"""Decision traces: every gate decision is recorded so it can be shown, audited and learned from."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, List, Optional


def _default_path() -> str:
    base = os.environ.get("STORAGE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "storage")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "decider_traces.jsonl")


class TraceStore:
    def __init__(self, path: Optional[str] = None, capacity: int = 500) -> None:
        self.path = path or _default_path()
        self._items: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f.readlines()[-capacity:]:
                    try:
                        self._items.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            pass

    def add(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        trace.setdefault("id", uuid.uuid4().hex[:12])
        trace.setdefault("ts", time.time())
        with self._lock:
            self._items.append(trace)
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(trace, default=str) + "\n")
            except OSError:
                pass
        return trace

    def get(self, trace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for t in reversed(self._items):
                if t.get("id") == trace_id:
                    return t
        return None

    def update(self, trace_id: str, **fields: Any) -> None:
        with self._lock:
            for t in self._items:
                if t.get("id") == trace_id:
                    t.update(fields)
                    return

    def recent(self, student_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        with self._lock:
            items = [t for t in self._items if student_id is None or t.get("student_id") == student_id]
        return list(reversed(items[-limit:]))

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            items = list(self._items)
        actions: Dict[str, int] = {}
        lat: List[float] = []
        for t in items:
            actions[t.get("action", "?")] = actions.get(t.get("action", "?"), 0) + 1
            if t.get("decider_mode") == "model" and t.get("decider_ms"):
                lat.append(float(t["decider_ms"]))
        lat.sort()
        med = lat[len(lat) // 2] if lat else None
        p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else None
        return {"total": len(items), "actions": actions, "decider_ms_median": med, "decider_ms_p95": p95}


_store: Optional[TraceStore] = None


def get_traces() -> TraceStore:
    global _store
    if _store is None:
        _store = TraceStore()
    return _store
