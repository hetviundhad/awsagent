"""
Synchronous client for a locally served Strands Decider 2B model.

    strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099

Wire format (verified against the official repo / AWS Builder Center write-ups):

    POST {url}/v1/systemone
    {"state": <text>, "model": "...", "questions": {key: {type, instructions, criteria}}}
    -> {"answers": {key: {...}}, "latency_ms": float, "usage": {"input_tokens": int}}

    noul   -> {"noul": P(true)}
    choice -> {"choice": name, "probabilities": {name: p}}
    score  -> {"score": float}

Design rules baked in here (all learned the hard way by other builders):
  * Ask EVERYTHING in one request - the state is encoded once and shared.
  * Never trust a bare number - every answer is returned with the probability
    so the CALLER (plain Python) decides what to do with it.
  * A circuit breaker keeps the tutor fast when the server is down.
  * An offline heuristic fallback exists so the app never dies, but every
    fallback answer is flagged `fallback=True` and surfaced in the UI. It is
    NEVER presented as a real model decision.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional

DEFAULT_URL = os.environ.get("STRANDS_DECIDER_URL") or (
    "http://" + os.environ.get("STRANDS_DECIDER_HOST", "127.0.0.1:8099")
)
MODEL_ID = "hobson-latest"
SERVE_HINT = "strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099"


class ServerUnavailable(RuntimeError):
    """Decider server is not reachable."""


# --------------------------------------------------------------------------- #
# Question builders (typed questions)                                         #
# --------------------------------------------------------------------------- #
def noul(instructions: str, true: str = "", false: str = "") -> Dict[str, Any]:
    """Yes/no. Answer is P(true). Write `true`/`false` criteria carefully - they sharpen the boundary."""
    q: Dict[str, Any] = {"type": "noul", "instructions": instructions}
    if true or false:
        q["criteria"] = {"true": true, "false": false}
    return q


def choice(instructions: str, options: Mapping[str, str]) -> Dict[str, Any]:
    """Pick one of N. `options` maps name -> one-line description (descriptions matter a lot)."""
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score(instructions: str, levels: List[str]) -> Dict[str, Any]:
    """Ordered rubric, lowest first. (Per the model card, prefer noul/choice for anything that matters.)"""
    return {"type": "score", "instructions": instructions, "criteria": list(levels)}


# --------------------------------------------------------------------------- #
# Normalised answer                                                           #
# --------------------------------------------------------------------------- #
@dataclass
class Answer:
    key: str
    kind: str                       # noul | choice | score
    p_true: Optional[float] = None  # noul
    choice: Optional[str] = None    # choice
    probabilities: Dict[str, float] = field(default_factory=dict)
    score: Optional[float] = None
    confidence: float = 0.0         # the number the caller branches on
    fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "kind": self.kind, "p_true": self.p_true, "choice": self.choice,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "score": self.score, "confidence": round(self.confidence, 4), "fallback": self.fallback,
        }


def _parse_answer(key: str, kind: str, raw: Mapping[str, Any]) -> Answer:
    if kind == "noul":
        p = float(raw.get("noul", raw.get("probability", 0.5)))
        return Answer(key, kind, p_true=p, confidence=max(p, 1 - p))
    if kind == "choice":
        probs = {str(k): float(v) for k, v in (raw.get("probabilities") or {}).items()}
        ch = raw.get("choice")
        if ch is None and probs:
            ch = max(probs, key=probs.get)
        conf = probs.get(ch, float(raw.get("confidence", 0.0))) if ch is not None else 0.0
        return Answer(key, kind, choice=ch, probabilities=probs, confidence=conf)
    s = float(raw.get("score", 0.0))
    return Answer(key, kind, score=s, confidence=float(raw.get("confidence", 0.5)))


@dataclass
class AskResult:
    answers: Dict[str, Answer]
    latency_ms: float
    mode: str                       # "model" | "fallback" | "unavailable"
    input_tokens: int = 0
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Client                                                                      #
# --------------------------------------------------------------------------- #
class DeciderClient:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 30.0,
                 allow_fallback: Optional[bool] = None,
                 breaker_failures: int = 3, breaker_cooldown: float = 20.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout
        if allow_fallback is None:
            allow_fallback = os.environ.get("DECIDER_ALLOW_FALLBACK", "true").lower() in ("1", "true", "yes")
        self.allow_fallback = allow_fallback
        self._fail_n = 0
        self._open_until = 0.0
        self._breaker_failures = breaker_failures
        self._breaker_cooldown = breaker_cooldown
        self._lock = threading.Lock()
        self.stats = {"calls": 0, "model_calls": 0, "fallback_calls": 0, "errors": 0,
                      "total_model_latency_ms": 0.0}

    # -- health ---------------------------------------------------------------
    def health(self, timeout: float = 3.0) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(f"{self.url}/health", timeout=timeout) as r:
                data = json.loads(r.read())
            self._reset_breaker()
            return {"ok": True, **data}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "hint": SERVE_HINT}

    @property
    def breaker_open(self) -> bool:
        return time.time() < self._open_until

    def _reset_breaker(self) -> None:
        with self._lock:
            self._fail_n = 0
            self._open_until = 0.0

    def _record_failure(self) -> None:
        with self._lock:
            self._fail_n += 1
            self.stats["errors"] += 1
            if self._fail_n >= self._breaker_failures:
                self._open_until = time.time() + self._breaker_cooldown

    # -- ask ------------------------------------------------------------------
    def ask(self, state: str, questions: Mapping[str, Dict[str, Any]],
            fallbacks: Optional[Mapping[str, Callable[[str], Dict[str, Any]]]] = None) -> AskResult:
        """Evaluate `state` against every question in ONE round trip."""
        self.stats["calls"] += 1
        if not self.breaker_open:
            body = json.dumps({"state": state, "model": MODEL_ID, "questions": dict(questions)}).encode()
            req = urllib.request.Request(f"{self.url}/v1/systemone", data=body,
                                         headers={"content-type": "application/json"})
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as res:
                    payload = json.loads(res.read())
                wall = (time.perf_counter() - t0) * 1000
                answers = {k: _parse_answer(k, questions[k]["type"], v)
                           for k, v in payload["answers"].items() if k in questions}
                lat = float(payload.get("latency_ms") or wall)
                self._reset_breaker()
                self.stats["model_calls"] += 1
                self.stats["total_model_latency_ms"] += lat
                return AskResult(answers, lat, "model",
                                 int((payload.get("usage") or {}).get("input_tokens", 0)))
            except (urllib.error.URLError, TimeoutError, ConnectionError, KeyError, ValueError) as exc:
                self._record_failure()
                err = f"{type(exc).__name__}: {exc}"
        else:
            err = "circuit breaker open (server recently unreachable)"

        if self.allow_fallback:
            return self._fallback(state, questions, fallbacks or {}, err)
        return AskResult({}, 0.0, "unavailable", error=err)

    # -- offline fallback (clearly labelled, never a real decision) -------------
    def _fallback(self, state: str, questions: Mapping[str, Dict[str, Any]],
                  fallbacks: Mapping[str, Callable[[str], Dict[str, Any]]], err: str) -> AskResult:
        self.stats["fallback_calls"] += 1
        t0 = time.perf_counter()
        out: Dict[str, Answer] = {}
        for key, q in questions.items():
            kind = q["type"]
            if key in fallbacks:
                raw = fallbacks[key](state)
            elif kind == "choice":
                raw = _lexical_choice(state, q.get("criteria", {}))
            elif kind == "noul":
                raw = {"noul": 0.5}
            else:
                raw = {"score": 0.0, "confidence": 0.0}
            a = _parse_answer(key, kind, raw)
            a.fallback = True
            out[key] = a
        return AskResult(out, (time.perf_counter() - t0) * 1000, "fallback", error=err)


def _tok(text: str) -> set:
    import re
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2}


def _lexical_choice(state: str, options: Mapping[str, str]) -> Dict[str, Any]:
    """Generic token-overlap picker. Deliberately weak; only used when the model is unreachable."""
    st = _tok(state)
    raw = {name: 0.05 + len(st & _tok(f"{name} {desc}")) for name, desc in options.items()}
    total = sum(raw.values()) or 1.0
    probs = {k: v / total for k, v in raw.items()}
    return {"choice": max(probs, key=probs.get), "probabilities": probs}


_client: Optional[DeciderClient] = None


def get_client() -> DeciderClient:
    global _client
    if _client is None:
        _client = DeciderClient()
    return _client
