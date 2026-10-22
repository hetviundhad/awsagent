"""
A real Strands agent for StudyMind whose tool calls are guarded by Decider 2B.

    Bedrock (Claude) -> writes text, picks tool calls
    Decider 2B       -> InterventionHandler.before_tool_call: "did the STUDENT actually name that concept?"
                        Proceed  -> tool runs
                        Guide    -> the agent is handed its turn back with feedback ("ask which concept")

The guard is GENERIC (`DeciderToolGuard`): it inspects whatever tool + arguments the agent proposes and builds a
specific yes/no question per argument at call time - no hard-coded tool names. Drop it into any Strands agent.
Verified API surface: strands.Agent(interventions=[...]), InterventionHandler.before_tool_call(event),
event.tool_use['name'|'input'], event.agent.messages, Proceed(), Guide(feedback=...).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence

from . import patterns as P
from .calibration import get_thresholds
from .client import get_client

try:                                                     # real Strands
    from strands.interventions import Guide, InterventionHandler, Proceed
    STRANDS_AVAILABLE = True
except Exception:                                        # noqa: BLE001  (lets the guard be unit-tested without strands)
    STRANDS_AVAILABLE = False

    class InterventionHandler:                           # type: ignore[no-redef]
        name = "handler"

    class Proceed:                                       # type: ignore[no-redef]
        def __repr__(self) -> str:
            return "Proceed()"

    class Guide:                                         # type: ignore[no-redef]
        def __init__(self, feedback: str = "") -> None:
            self.feedback = feedback

        def __repr__(self) -> str:
            return f"Guide({self.feedback!r})"

# Tool arguments that are free-text / structural and therefore can't be "grounded" by naming them.
SKIP_ARGS = {"top_k", "limit", "n", "count", "k", "max_results", "num_questions"}


def student_text(messages: Sequence[Dict[str, Any]]) -> str:
    """ONLY what the student said. The agent's own 'Let me check X' would make guessed values look grounded."""
    return "\n".join(f"student: {b['text']}" for m in messages if m.get("role") == "user"
                     for b in m.get("content", []) if isinstance(b, dict) and "text" in b)


class DeciderToolGuard(InterventionHandler):
    """#guardrails - before ANY tool runs, verify its string arguments are grounded in the student's own words."""
    name = "decider_tool_guard"

    def __init__(self, client=None, thresholds=None, log: Optional[List[Dict[str, Any]]] = None) -> None:
        self.client = client or get_client()
        self.thresholds = thresholds or get_thresholds()
        self.log: List[Dict[str, Any]] = log if log is not None else []

    def _check(self, tool: str, args: Dict[str, Any], talk: str) -> Dict[str, Any]:
        pats = [P.grounded_tool_arg(tool, a, v) for a, v in args.items()
                if isinstance(v, str) and v.strip() and a not in SKIP_ARGS]
        if not pats:
            return {"verdict": "proceed", "decisions": [], "reason": "no string arguments to ground"}
        state = (f"--- CONVERSATION ---\n{talk}\n\n--- PROPOSED TOOL CALL ---\n"
                 f"tool: {tool}\narguments: {json.dumps(args)}")
        decisions, ask = P.run_patterns(self.client, state, pats, self.thresholds.get)
        bad = [d for d in decisions.values() if d.triggered and not d.fallback]
        return {"verdict": "guide" if bad else "proceed", "decisions": [d.to_dict() for d in decisions.values()],
                "mode": ask.mode, "ms": ask.latency_ms, "ungrounded": [d.key.replace("grounded_", "") for d in bad]}

    def before_tool_call(self, event, **kwargs):
        tool = event.tool_use["name"]
        args = event.tool_use.get("input") or {}
        try:
            r = self._check(tool, args, student_text(event.agent.messages))
        except Exception as exc:  # noqa: BLE001 - guardrail must fail OPEN, never wedge the tutor
            self.log.append({"tool": tool, "args": args, "verdict": "proceed", "error": str(exc)})
            return Proceed()
        self.log.append({"tool": tool, "args": args, **r})
        if r["verdict"] == "guide":
            names = ", ".join(r["ungrounded"])
            return Guide(feedback=(f"The student never mentioned the value you used for: {names}. "
                                   "Do not guess. Ask the student which one they mean, then call the tool."))
        return Proceed()


class StrandsProactivityGuard(InterventionHandler):
    """#policy - determines when the agent should speak, guide, or stay silent.
    Sits in the agent's path and guards against excessive or untimely AI chatter."""
    name = "strands_proactivity_guard"

    def __init__(self, gate: Optional[P.ProactivityGate] = None, log: Optional[List[Dict[str, Any]]] = None) -> None:
        self.gate = gate or P.ProactivityGate(get_client())
        self.log: List[Dict[str, Any]] = log if log is not None else []

    def before_tool_call(self, event, **kwargs):
        # Allow tool call to proceed normally
        return Proceed()

    def before_generate(self, event, **kwargs):
        """Called before the agent generates words. If gate dictates silence, holds the agent back."""
        try:
            talk = student_text(event.agent.messages)
            res = self.gate.evaluate(talk)
            self.log.append({"action": res.action, "rung": res.rung, "held_back_by": res.held_back_by})
            if not res.spoken and res.action == "silence":
                return Guide(feedback="The user is productively thinking. Stay silent and do not interrupt.")
        except Exception:
            pass
        return Proceed()



# --------------------------------------------------------------------------- #
def build_agent(course_id: str, student_id: str, log: List[Dict[str, Any]]):
    """Strands agent over StudyMind's own retrieval + learner model. Raises RuntimeError if strands isn't installed."""
    if not STRANDS_AVAILABLE:
        raise RuntimeError("strands-agents is not installed: pip install strands-agents 'botocore[crt]'")
    from strands import Agent, tool
    from strands.models import BedrockModel

    @tool
    def search_course_material(query: str) -> str:
        """Search the student's uploaded course material.

        Args:
            query: the concept or question to look up in the course material
        """
        from backend.app.rag.engine import rag_engine
        chunks = rag_engine.retrieve_chunks(course_id, query, top_k=4)
        if not chunks:
            return "No matching material found."
        return "\n\n".join(f"[{i + 1}] {c.get('document_name', 'doc')}: {c.get('content', '')[:600]}" for i, c in enumerate(chunks))

    @tool
    def get_concept_mastery(concept_name: str) -> str:
        """Look up how well the student currently knows one concept.

        Args:
            concept_name: the exact concept the student asked about
        """
        from backend.app.learner.bkt import bkt_engine
        rows = bkt_engine.get_learner_profile(student_id, course_id).get("mastery_by_concept", [])
        hit = next((r for r in rows if concept_name.lower() in r["concept_name"].lower()), None)
        if not hit:
            return f"No mastery record for '{concept_name}'."
        return f"{hit['concept_name']}: {hit['mastery_probability']:.0%} mastery" + (" (locked)" if hit.get("is_locked") else "")

    @tool
    def list_weak_concepts() -> str:
        """List the concepts the student is currently weakest at."""
        from backend.app.learner.bkt import bkt_engine
        rows = bkt_engine.get_learner_profile(student_id, course_id).get("mastery_by_concept", [])
        weak = sorted((r for r in rows if not r.get("is_locked")), key=lambda r: r["mastery_probability"])[:5]
        return "\n".join(f"{r['concept_name']}: {r['mastery_probability']:.0%}" for r in weak) or "No data yet."

    model = BedrockModel(model_id=os.environ.get("BEDROCK_MODEL_FAST", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
                         region_name=os.environ.get("AWS_REGION", "us-east-1"))
    system = ("You are StudyMind's study agent. Use the tools to answer from the student's own course material. "
              "Be concise. Never invent course content.")
    return Agent(model=model, tools=[search_course_material, get_concept_mastery, list_weak_concepts],
                 interventions=[DeciderToolGuard(log=log)], system_prompt=system, callback_handler=None)


def run_agent(course_id: str, student_id: str, message: str) -> Dict[str, Any]:
    log: List[Dict[str, Any]] = []
    agent = build_agent(course_id, student_id, log)
    t0 = time.perf_counter()
    out = agent(message)
    return {"answer": str(out), "guard_events": log, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
