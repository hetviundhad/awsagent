"""
Run with:  python -m unittest backend.tests.test_decider -v     (or pytest)
Stdlib only: the decider package is importable without FastAPI / boto3 / strands.
Uses the MOCK server (keyword rules) to verify plumbing, thresholds, fail-open and guard logic.
"""
import os
import sys
import tempfile
import threading
import unittest
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from backend.app.decider import patterns as P                      # noqa: E402
from backend.app.decider.calibration import ThresholdStore         # noqa: E402
from backend.app.decider.client import DeciderClient                # noqa: E402
from backend.app.decider.gate import CourseProfile, LearnerSnapshot, StudyGate  # noqa: E402
from backend.app.decider.trace import TraceStore                    # noqa: E402
import mock_decider_server as mock                                  # noqa: E402

COURSE = CourseProfile("Algorithms", ["Dynamic Programming", "Graph Algorithms", "Sorting"])


def _serve():
    srv = HTTPServer(("127.0.0.1", 0), mock.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = _serve()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def gate(self, url=None, **kw):
        d = tempfile.mkdtemp()
        return StudyGate(DeciderClient(url or self.url, allow_fallback=kw.get("fb", True), timeout=3),
                         ThresholdStore(os.path.join(d, "t.json")), TraceStore(os.path.join(d, "tr.jsonl")))

    def run_gate(self, g, msg, weak=()):
        return g.evaluate(message=msg, course=COURSE, learner=LearnerSnapshot(weak=list(weak)), student_id="s1", course_id="c1")

    def test_one_round_trip_for_all_questions(self):
        g = self.gate()
        self.run_gate(g, "Explain how dynamic programming avoids recomputation", weak=["Recursion"])
        self.assertEqual(g.client.stats["model_calls"], 1)            # policy+clarity+complexity+prereq in ONE request

    def test_policy_actions(self):
        g = self.gate()
        self.assertEqual(self.run_gate(g, "quiz me on graph algorithms please").action, "quiz")
        self.assertEqual(self.run_gate(g, "I'm so overwhelmed and stressed about the exam").action, "support")
        self.assertEqual(self.run_gate(g, "what is a good movie recipe for tonight").action, "redirect")
        r = self.run_gate(g, "just give me the answer to question 3 of my homework")
        self.assertEqual((r.action, r.mode_override), ("socratic", "Socratic"))

    def test_vague_message_triggers_clarify(self):
        self.assertEqual(self.run_gate(self.gate(), "explain it more?").action, "clarify")

    def test_routing_tier(self):
        g = self.gate()
        self.assertEqual(self.run_gate(g, "Derive the time complexity of merge sort and compare it with quicksort").route["tier"], "deep")
        self.assertEqual(self.run_gate(g, "What is a stack in data structures").route["tier"], "fast")

    def test_prereq_hint_only_when_weak(self):
        g = self.gate()
        self.assertIn("Recursion", self.run_gate(g, "Explain recursion tree for dynamic programming", weak=["Recursion"]).learner_hint)
        self.assertEqual(self.run_gate(g, "Explain recursion tree for dynamic programming").learner_hint, "")

    def test_chitchat_skips_decider(self):
        g = self.gate()
        r = self.run_gate(g, "thanks")
        self.assertEqual((r.decider_mode, g.client.stats["calls"]), ("skipped", 0))

    def test_fails_open_when_server_down_and_labels_fallback(self):
        g = self.gate(url="http://127.0.0.1:9", fb=True)
        r = self.run_gate(g, "Explain dynamic programming with an example")
        self.assertEqual(r.decider_mode, "fallback")
        self.assertTrue(all(d["fallback"] for d in r.decisions))        # never passed off as a real decision
        g2 = self.gate(url="http://127.0.0.1:9", fb=False)
        r2 = self.run_gate(g2, "Explain dynamic programming with an example")
        self.assertEqual((r2.action, r2.decider_mode), ("answer", "unavailable"))

    def test_circuit_breaker_opens(self):
        c = DeciderClient("http://127.0.0.1:9", allow_fallback=True, timeout=1, breaker_failures=2, breaker_cooldown=60)
        for _ in range(3):
            c.ask("x", {"q": P.clarity_check().question()})
        self.assertTrue(c.breaker_open)

    def test_trace_recorded(self):
        g = self.gate()
        r = self.run_gate(g, "Explain graph algorithms like BFS")
        self.assertIsNotNone(g.traces.get(r.trace_id))

    def test_context_scoring_never_empties(self):
        g = self.gate()
        chunks = [{"id": "a", "content": "bananas and apples"}, {"id": "b", "content": "football scores"}]
        out = g.score_context("explain dynamic programming memoization", chunks)
        self.assertGreaterEqual(len(out), 1)

    def test_thresholds_adapt_and_stay_bounded(self):
        t = ThresholdStore(os.path.join(tempfile.mkdtemp(), "t.json"))
        before = t.get("clarity")
        # gate asked a clarifying question and the student said that was NOT helpful -> be less eager (lower value)
        t.feedback({"threshold_key": "clarity", "triggered": True, "measure": 0.2}, helpful=False)
        self.assertLess(t.get("clarity"), before)
        for _ in range(100):
            t.feedback({"threshold_key": "clarity", "triggered": True, "measure": 0.2}, helpful=False)
        self.assertGreaterEqual(t.get("clarity"), 0.15)
        # fallback decisions must never tune thresholds
        self.assertFalse(t.feedback({"threshold_key": "policy", "triggered": True, "measure": .5, "fallback": True}, False)["changed"])


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = _serve()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_tool_guard_guides_on_guessed_arg_and_proceeds_when_grounded(self):
        from backend.app.decider.strands_agent import DeciderToolGuard

        class Ev:
            def __init__(self, text, concept):
                self.agent = type("A", (), {"messages": [{"role": "user", "content": [{"text": text}]},
                                                         {"role": "assistant", "content": [{"text": f"Let me check {concept}"}]}]})()
                self.tool_use = {"name": "get_concept_mastery", "input": {"concept_name": concept}}
        d = tempfile.mkdtemp()
        guard = DeciderToolGuard(DeciderClient(self.url, timeout=3), ThresholdStore(os.path.join(d, "t.json")))
        self.assertEqual(type(guard.before_tool_call(Ev("how am I doing?", "Dynamic Programming"))).__name__, "Guide")
        self.assertEqual(type(guard.before_tool_call(Ev("how am I doing in Dynamic Programming?", "Dynamic Programming"))).__name__, "Proceed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
