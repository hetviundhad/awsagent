"""
Adaptive confidence thresholds.

The Decider gives probabilities; *your code* decides what a probability means.
Static thresholds go stale, so StudyMind learns them from student feedback:

  * A student marks a reply 👎 after the gate TRIGGERED an action (e.g. asked a
    clarifying question)            -> the gate was too eager -> make it harder to trigger.
  * A student marks a reply 👎 when the gate stayed quiet but the decision was a
    near miss (within MARGIN of its threshold)
                                    -> the gate was too lax   -> make it easier to trigger.
  * 👍 on a triggered action just records support (no drift).

Every change is bounded, logged and visible in the Decision Lab.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List

DEFAULTS: Dict[str, Dict[str, float]] = {
    # key        value  lo    hi    step   (value = P needed to TRIGGER the action)
    "policy":     {"value": 0.50, "lo": 0.35, "hi": 0.85, "step": 0.02},   # min confidence to trust the policy label
    "clarity":    {"value": 0.35, "lo": 0.15, "hi": 0.60, "step": 0.02},   # ask clarification when P(specific) < value
    "complexity": {"value": 0.60, "lo": 0.45, "hi": 0.85, "step": 0.02},   # route to deep model when P(complex) >= value
    "prereq":     {"value": 0.65, "lo": 0.50, "hi": 0.90, "step": 0.02},   # prepend prerequisite hint when P >= value
    "relevance":  {"value": 0.40, "lo": 0.20, "hi": 0.70, "step": 0.02},   # keep context chunk when P(relevant) >= value
    "grounded":   {"value": 0.65, "lo": 0.50, "hi": 0.90, "step": 0.02},   # guardrail: block tool call when P(grounded) < value
    # Silence Engine adaptive thresholds
    "silence_shield":        {"value": 0.60, "lo": 0.35, "hi": 0.85, "step": 0.03},  # productive-struggle shield (P >= value forces silence)
    "silence_frustration":   {"value": 0.70, "lo": 0.45, "hi": 0.90, "step": 0.03},  # triggers breather first when P >= value
    "silence_help":          {"value": 0.65, "lo": 0.40, "hi": 0.90, "step": 0.03},  # jumps directly to Rung 3 when P >= value
    "silence_stuck":         {"value": 0.60, "lo": 0.35, "hi": 0.85, "step": 0.03},  # triggers escalation ladder when P(stuck/wrong) >= value
    "silence_suspect":       {"value": 0.60, "lo": 0.35, "hi": 0.85, "step": 0.03},  # flags suspect line for ghost underline
    "silence_progress":      {"value": 0.50, "lo": 0.35, "hi": 0.85, "step": 0.02},  # progress classification confidence
    "silence_misconception": {"value": 0.50, "lo": 0.35, "hi": 0.85, "step": 0.02},  # Atlas misconception confidence
}
INVERTED = {"clarity", "grounded"}   # these trigger when P is LOW, so a higher value = MORE eager
MARGIN = 0.12


def _default_path() -> str:
    base = os.environ.get("STORAGE_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "storage")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "decider_thresholds.json")


class ThresholdStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or _default_path()
        self._lock = threading.Lock()
        self.state: Dict[str, Any] = {"values": {k: v["value"] for k, v in DEFAULTS.items()},
                                      "history": [], "feedback_events": 0}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in (saved.get("values") or {}).items():
                if k in DEFAULTS:
                    self.state["values"][k] = float(v)
            self.state["history"] = saved.get("history", [])[-100:]
            self.state["feedback_events"] = int(saved.get("feedback_events", 0))
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def get(self, key: str) -> float:
        return float(self.state["values"].get(key, DEFAULTS[key]["value"]))

    def snapshot(self) -> Dict[str, Any]:
        return {"values": dict(self.state["values"]), "defaults": {k: v["value"] for k, v in DEFAULTS.items()},
                "bounds": {k: [v["lo"], v["hi"]] for k, v in DEFAULTS.items()},
                "feedback_events": self.state["feedback_events"], "history": self.state["history"][-15:]}

    def feedback(self, decision: Dict[str, Any], helpful: bool) -> Dict[str, Any]:
        """`decision` is one entry of a trace's `decisions` list."""
        key = decision.get("threshold_key")
        if key not in DEFAULTS or decision.get("fallback"):
            return {"changed": False, "reason": "decision not tunable (fallback or unknown key)"}
        with self._lock:
            self.state["feedback_events"] += 1
            d = DEFAULTS[key]
            thr = self.get(key)
            triggered = bool(decision.get("triggered"))
            p = float(decision.get("measure", 0.0))
            direction = 0
            if not helpful:
                if triggered:
                    direction = +1          # too eager -> raise bar to trigger
                elif abs(p - thr) <= MARGIN:
                    direction = -1          # near miss -> lower bar
            # inverted keys trigger when P is LOW, so a higher value = MORE eager
            if key in INVERTED:
                direction = -direction
            new = min(d["hi"], max(d["lo"], thr + direction * d["step"]))
            changed = abs(new - thr) > 1e-9
            if changed:
                self.state["values"][key] = round(new, 4)
                self.state["history"].append({"ts": time.time(), "key": key, "from": round(thr, 4),
                                              "to": round(new, 4), "helpful": helpful, "triggered": triggered})
                self.state["history"] = self.state["history"][-100:]
            self._save()
            return {"changed": changed, "key": key, "from": round(thr, 4), "to": round(new, 4)}

    def reset(self) -> None:
        with self._lock:
            self.state = {"values": {k: v["value"] for k, v in DEFAULTS.items()}, "history": [], "feedback_events": 0}
            self._save()


_store: ThresholdStore | None = None


def get_thresholds() -> ThresholdStore:
    global _store
    if _store is None:
        _store = ThresholdStore()
    return _store
