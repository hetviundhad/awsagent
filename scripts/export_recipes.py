#!/usr/bin/env python3
"""Regenerates decision_patterns/recipes/*.json from the live pattern factories (single source of truth)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.decider import patterns as P            # noqa: E402
from backend.app.decider.calibration import DEFAULTS      # noqa: E402

OUT = ROOT / "decision_patterns" / "recipes"
OUT.mkdir(parents=True, exist_ok=True)

WIRING_GATE = """\
from backend.app.decider import patterns as P
from backend.app.decider.client import get_client
from backend.app.decider.calibration import get_thresholds

thr = get_thresholds()
decisions, ask = P.run_patterns(get_client(), state, [{factory}], thr.get)   # ONE round trip for all patterns
d = decisions["{key}"]
if d.triggered:          # plain Python owns the control flow
    ...                  # {on_trigger}
"""

recipes = [
    ("policy", "#policy", P.pedagogy_policy("Algorithms", ["Dynamic Programming", "Graph Algorithms"]),
     "P.pedagogy_policy(course_name, topic_names)", "map d.action -> answer | quiz | socratic | support | redirect",
     "Option descriptions are generated from the live course, so the same recipe adapts to any subject. 'none_of_these' is mandatory."),
    ("clarity", "#policy", P.clarity_check(), "P.clarity_check()",
     "ask ONE clarifying question instead of guessing (Guide-style)",
     "Triggers when P(specific) is LOW. Show only STUDENT messages in the state."),
    ("model-routing", "#model-routing", P.complexity_router(), "P.complexity_router()",
     "use the deep model tier; otherwise the fast tier",
     "Cheap, high-frequency decision: ~one forward pass instead of an LLM call per message."),
    ("prerequisite-gap", "#context-memory", P.prereq_gap(["Recursion", "Big-O"]), "P.prereq_gap(weak_concepts)",
     "prepend a prerequisite nudge to the prompt",
     "Returns None when the learner model has no weak concepts, so the question is simply not asked."),
    ("context-relevance", "#context-memory", P.context_relevance(), "P.context_relevance()",
     "keep the chunk when triggered; drop it otherwise (never drop all chunks)",
     "One request per chunk, time-boxed. State = question + '--- EXCERPT ---' + chunk."),
    ("tool-argument-guardrail", "#guardrails", P.grounded_tool_arg("get_concept_mastery", "concept_name", "Dynamic Programming"),
     "P.grounded_tool_arg(tool, arg, value)  # built per call by DeciderToolGuard",
     "return Guide(feedback='Ask the student which concept they mean')",
     "Question text is generated per tool argument at call time. Use inside a Strands InterventionHandler (see strands_agent.py)."),
    ("proactivity_gate", "#policy", P.silence_signals()[1],  # productive_struggle
     "P.ProactivityGate(client, shield=0.60, hysteresis_ticks=3, max_budget=4)",
     "res = gate.evaluate(user_text); if not res.spoken: stay_silent()",
     "How to use this recipe: Wrap your agent loop with ProactivityGate. Continuous ~1s background ticks watch user working. If user is in productive struggle, shield them in silence (0 tokens). Only escalate when stuck across multiple ticks."),
]
for name, tag, pat, factory, on_trigger, note in recipes:
    thr_key = pat.threshold_key
    card = {
        "name": name, "hackathon_tag": tag, "model": "StrandsAgents/strands-decider-2B-hobson-v19",
        "how_to_use": note,
        "question": pat.question(), "state_shape": "see P.build_state(...) - only the user's/student's own words",
        "threshold": {"key": thr_key, "default": DEFAULTS[thr_key]["value"], "adapts_from_feedback": True,
                      "triggers_when": getattr(pat, "trigger_when", "top choice confidence >= threshold")},
        "wiring": WIRING_GATE.format(factory=factory, key=pat.key, on_trigger=on_trigger),
        "note": note,
    }
    (OUT / f"{name}.json").write_text(json.dumps(card, indent=2))
    print("wrote", name)

