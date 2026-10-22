#!/usr/bin/env python3
"""
MOCK Strands Decider server - for plumbing tests and offline UI development ONLY.

It speaks the same wire format as `strands-decider serve` (POST /v1/systemone, GET /health) but answers with
transparent keyword rules, NOT the 2B model. /health reports "mock": true and the Decision Lab shows a banner.
NEVER use its numbers in the article, the benchmark or the demo video as if they were model decisions.

    python tools/mock_decider_server.py --port 8099
"""
import argparse
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.decider import patterns as P  # noqa: E402


def noul_rule(instr: str, state: str) -> float:
    low = instr.lower()
    msg = P.latest_message(state)
    if "specific enough" in low:
        return 0.15 if len(msg.split()) <= 3 else 0.8
    if "multi-step reasoning" in low:
        return 0.8 if re.search(r"derive|prove|design|compare|trade|implement|optimi|analy|why does", msg.lower()) or len(msg.split()) > 28 else 0.2
    if "weak concepts" in low:
        m = re.search(r"weak concepts: (.*)", state)
        weak = [w.strip().lower() for w in (m.group(1) if m else "").split(",") if w.strip() and w.strip() != "none"]
        return 0.85 if any(w in msg.lower() for w in weak) else 0.15
    if "excerpt" in low:
        q = set(re.findall(r"[a-z0-9]{4,}", state.split("--- EXCERPT ---")[0].lower()))
        e = set(re.findall(r"[a-z0-9]{4,}", state.split("--- EXCERPT ---")[-1].lower()))
        return min(0.95, 0.1 + 2.5 * len(q & e) / (len(q) or 1))
    m = re.search(r"mention or clearly ask about '(.+?)'", instr)
    if m:
        said = state.split("--- PROPOSED TOOL CALL ---")[0].lower()
        return 0.85 if m.group(1).lower() in said else 0.2
    # Silence Engine rules
    if "real, reasoned attempt" in low:
        if "i give up" in state.lower() or "(empty scratchpad)" in state:
            return 0.15
        if "reasoned attempt" in state.lower() or "step" in state.lower() or len(state.split()) > 35:
            return 0.82
        return 0.45
    if "frustration" in low or "wanting to quit" in low:
        return 0.88 if re.search(r"frustrated|give up|hate this|can't do|impossible|quit|stuck", state.lower()) else 0.12
    if "explicitly ask for help" in low:
        return 0.92 if re.search(r"\b(help|hint|please explain|how do i)\b", state.lower()) else 0.05
    if "contain the misconception" in low:
        return 0.85 if re.search(r"wrong|error|mistake|misconception|false", state.lower()) else 0.20
    return 0.5


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            return self._send({"checkpoint": "MOCK-keyword-rules", "base_model": "none", "device": "cpu",
                               "max_length": 4096, "mock": True})
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/v1/systemone":
            return self._send({"error": "not found"}, 404)
        t0 = time.perf_counter()
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        state, answers = body["state"], {}
        for key, q in body["questions"].items():
            if q["type"] == "noul":
                answers[key] = {"type": "noul", "noul": noul_rule(q["instructions"], state)}
            elif q["type"] == "choice":
                opts = q["criteria"]
                if "explain_concept" in opts:
                    probs = {k: v for k, v in P._policy_heuristic(state).items() if k in opts}
                    s = sum(probs.values()) or 1
                    probs = {k: v / s for k, v in probs.items()}
                elif "moving_forward" in opts:
                    from backend.app.silence.signals import _progress_heuristic
                    probs = _progress_heuristic(state, state)
                else:
                    from backend.app.decider.client import _lexical_choice
                    probs = _lexical_choice(state, opts)["probabilities"]
                answers[key] = {"type": "choice", "choice": max(probs, key=probs.get), "probabilities": probs}
            else:
                answers[key] = {"type": "score", "score": 0.0}
        self._send({"model": "mock", "answers": answers, "latency_ms": (time.perf_counter() - t0) * 1000,
                    "usage": {"input_tokens": len(state.split())}})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    a = ap.parse_args()
    print(f"MOCK decider on :{a.port}  (keyword rules, NOT the 2B model)")
    HTTPServer(("127.0.0.1", a.port), H).serve_forever()
