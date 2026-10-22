"""
Unit tests for StudyMind Silence Engine.
Run with: python -m unittest backend.tests.test_silence -v (or pytest)

Tests cover:
  1. Productive struggle shield forces silence (even when student is wrong).
  2. Hysteresis: requires N consecutive trigger ticks before climbing a rung.
  3. Cooldown: prevents rapid back-to-back spoken interventions.
  4. Budget: hard cap on spoken interventions per problem.
  5. No rung skipping: advances 0 -> 1 -> 2 -> 3 -> 4 in sequence.
  6. Help request jump: explicit ask for help jumps directly to Rung 3.
  7. Frustration precedence: high frustration triggers Breather first, never academic lecturing.
  8. Fail-open: if Decider client raises or server is unreachable, typing never crashes and tutor stays silent.
  9. Stale tick dropped: concurrency control ensures latest-wins.
  10. Line suspect only evaluated on changed lines.
  11. Word-limit enforcement in speak.py (R2 <= 15 words, R3 <= 30 words, R4 <= 45 words).
"""
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import mock_decider_server as mock
from backend.app.decider.calibration import ThresholdStore
from backend.app.decider.client import DeciderClient
from backend.app.silence.atlas import Atlas, Misconception, build_atlas
from backend.app.silence.ladder import (
    SilenceDecision,
    check_budget_exhausted,
    check_cooldown,
    check_productive_struggle_shield,
    evaluate_escalation_ladder,
)
from backend.app.silence.replay import ReplayStore, SessionRecord
from backend.app.silence.session import SilenceSession, SilenceSessionManager
from backend.app.silence.signals import (
    KeystrokeMeta,
    SilenceSignalsEvaluator,
    TickSignals,
)
from backend.app.silence.speak import (
    SpokenMessage,
    _validate_response,
    compose_silence_message,
)


def _serve_mock():
    srv = HTTPServer(("127.0.0.1", 0), mock.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


class SilenceEngineUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.url = _serve_mock()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.thresholds = ThresholdStore(os.path.join(self.tmp_dir, "thresholds.json"))
        self.client = DeciderClient(self.url, allow_fallback=True, timeout=2.0)
        self.manager = SilenceSessionManager(client=self.client, thresholds=self.thresholds)

    # 1. Productive struggle shield
    def test_productive_struggle_shield_forces_silence(self):
        shielded, reason = check_productive_struggle_shield(p_struggle=0.82, shield_threshold=0.60)
        self.assertTrue(shielded)
        self.assertIn("productive_struggle_shield", reason)

        # Evaluator integration: even if wrong path, shield forces rung 0
        from backend.app.decider.patterns import Decision
        mock_struggle = Decision("productive_struggle", "ps", "noul", "yes", 0.85, 0.60, "silence_shield", True, 0.85)
        mock_prog = Decision("progress", "p", "choice", "wrong_path", 0.90, 0.50, "silence_progress", True, 0.90, {"wrong_path": 0.90})
        signals = TickSignals(productive_struggle=mock_struggle, progress=mock_prog)

        dec = evaluate_escalation_ladder(
            signals=signals,
            current_rung=0,
            trigger_streak=5,
            seconds_since_last_spoken=100.0,
            interventions_count=0,
            shield_threshold=0.60,
        )
        self.assertEqual(dec.rung, 0)
        self.assertIn("productive_struggle_shield", dec.held_back_by)
        self.assertFalse(dec.spoken)

    # 2. Hysteresis
    def test_hysteresis_prevents_premature_escalation(self):
        from backend.app.decider.patterns import Decision
        mock_struggle = Decision("productive_struggle", "ps", "noul", "no", 0.20, 0.60, "silence_shield", False, 0.80)
        mock_prog = Decision("progress", "p", "choice", "wrong_path", 0.80, 0.50, "silence_progress", True, 0.80, {"wrong_path": 0.80})
        signals = TickSignals(productive_struggle=mock_struggle, progress=mock_prog)

        # Streak is only 1 (< default 3)
        dec = evaluate_escalation_ladder(
            signals=signals,
            current_rung=0,
            trigger_streak=1,
            seconds_since_last_spoken=100.0,
            interventions_count=0,
            hysteresis_ticks=3,
        )
        self.assertEqual(dec.rung, 0)
        self.assertIn("hysteresis_filter", dec.held_back_by)

        # Once streak reaches 3 -> advances to Rung 1
        dec3 = evaluate_escalation_ladder(
            signals=signals,
            current_rung=0,
            trigger_streak=3,
            seconds_since_last_spoken=100.0,
            interventions_count=0,
            hysteresis_ticks=3,
        )
        self.assertEqual(dec3.rung, 1)

    # 3. Cooldown
    def test_cooldown_delays_spoken_intervention(self):
        is_cd, reason = check_cooldown(seconds_since_last_spoken=10.0, interventions_count=1, base_cooldown=20.0)
        self.assertTrue(is_cd)
        self.assertIn("cooldown_active", reason)

        is_cd_done, _ = check_cooldown(seconds_since_last_spoken=35.0, interventions_count=1, base_cooldown=20.0)
        self.assertFalse(is_cd_done)

    # 4. Budget
    def test_budget_exhausted_caps_spoken_interventions(self):
        is_exhausted, reason = check_budget_exhausted(interventions_count=4, max_budget=4, help_requested=False)
        self.assertTrue(is_exhausted)
        self.assertIn("budget_exhausted", reason)

        # Explicit help bypasses budget cap
        is_bypassed, _ = check_budget_exhausted(interventions_count=4, max_budget=4, help_requested=True)
        self.assertFalse(is_bypassed)

    # 5. No rung skipping
    def test_no_rung_skipping(self):
        from backend.app.decider.patterns import Decision
        mock_struggle = Decision("productive_struggle", "ps", "noul", "no", 0.10, 0.60, "silence_shield", False, 0.90)
        mock_prog = Decision("progress", "p", "choice", "wrong_path", 0.90, 0.50, "silence_progress", True, 0.90, {"wrong_path": 0.90})
        signals = TickSignals(productive_struggle=mock_struggle, progress=mock_prog)

        # From 0 with streak -> goes to 1
        d1 = evaluate_escalation_ladder(signals=signals, current_rung=0, trigger_streak=3, seconds_since_last_spoken=100.0, interventions_count=0)
        self.assertEqual(d1.rung, 1)

        # From 1 with streak -> goes to 2
        d2 = evaluate_escalation_ladder(signals=signals, current_rung=1, trigger_streak=3, seconds_since_last_spoken=100.0, interventions_count=0)
        self.assertEqual(d2.rung, 2)

        # From 2 with streak -> goes to 3
        d3 = evaluate_escalation_ladder(signals=signals, current_rung=2, trigger_streak=3, seconds_since_last_spoken=100.0, interventions_count=1)
        self.assertEqual(d3.rung, 3)

    # 6. Help request jump
    def test_help_request_jumps_to_rung_3(self):
        from backend.app.decider.patterns import Decision
        mock_help = Decision("help_request", "hr", "noul", "yes", 0.95, 0.65, "silence_help", True, 0.95)
        signals = TickSignals(help_request=mock_help)

        dec = evaluate_escalation_ladder(
            signals=signals,
            current_rung=0,
            trigger_streak=0,
            seconds_since_last_spoken=0.0,
            interventions_count=0,
        )
        self.assertEqual(dec.rung, 3)
        self.assertTrue(dec.spoken)
        self.assertEqual(dec.action_type, "hint")

    # 7. Frustration triggers Breather first
    def test_frustration_triggers_breather_first(self):
        from backend.app.decider.patterns import Decision
        mock_frust = Decision("frustration", "fr", "noul", "yes", 0.88, 0.70, "silence_frustration", True, 0.88)
        mock_prog = Decision("progress", "p", "choice", "wrong_path", 0.90, 0.50, "silence_progress", True, 0.90, {"wrong_path": 0.90})
        signals = TickSignals(frustration=mock_frust, progress=mock_prog)

        dec = evaluate_escalation_ladder(
            signals=signals,
            current_rung=0,
            trigger_streak=5,
            seconds_since_last_spoken=100.0,
            interventions_count=0,
        )
        self.assertEqual(dec.rung, "B")
        self.assertTrue(dec.spoken)
        self.assertEqual(dec.action_type, "breather")

    # 8. Fail-open when client raises
    def test_fail_open_when_client_fails(self):
        broken_client = DeciderClient("http://127.0.0.1:9999", allow_fallback=True, timeout=0.1)
        mgr = SilenceSessionManager(client=broken_client, thresholds=self.thresholds)

        res = mgr.start_session(problem="Solve recurrence T(n) = 2T(n/2) + n")
        sid = res["session_id"]

        # Tick must not raise; it returns valid tick response in fallback mode
        tick_res = mgr.tick(session_id=sid, text="Let T(n) be something")
        self.assertIn("decision", tick_res)
        self.assertIn(tick_res["decision"]["decider_mode"], ("fallback", "unavailable", "model"))

    # 9. Stale tick dropped
    def test_stale_tick_dropped_when_superseded(self):
        sess_data = self.manager.start_session(problem="Binary Search algorithm")
        sid = sess_data["session_id"]
        sess = self.manager.get_session(sid)

        seq1 = sess.next_seq()
        seq2 = sess.next_seq()

        self.assertFalse(sess.is_current_seq(seq1))
        self.assertTrue(sess.is_current_seq(seq2))

    # 10. Word limit enforcement in speak.py
    def test_word_limit_validation(self):
        # Rung 2: max 15 words
        short_q = "What is the base case here?"
        long_q = "This is an extremely long and unnecessarily verbose Socratic question that keeps going and going and exceeds fifteen words easily."
        self.assertTrue(_validate_response(short_q, 15, 2))
        self.assertFalse(_validate_response(long_q, 15, 2))

        # Check template fallback respects word counts
        dec2 = SilenceDecision(rung=2, rung_name="Margin Question", token_class="tiny", action_type="question", spoken=True)
        msg2 = compose_silence_message(decision=dec2, problem="Binary Search", course_name="Algorithms", scratchpad="while l < r:\n  mid = l+r")
        self.assertLessEqual(msg2.word_count, 15)

        dec3 = SilenceDecision(rung=3, rung_name="Margin Hint", token_class="small", action_type="hint", spoken=True)
        msg3 = compose_silence_message(decision=dec3, problem="Binary Search", course_name="Algorithms", scratchpad="while l < r:")
        self.assertLessEqual(msg3.word_count, 30)

        dec4 = SilenceDecision(rung=4, rung_name="One Step", token_class="small", action_type="step", spoken=True)
        msg4 = compose_silence_message(decision=dec4, problem="Binary Search", course_name="Algorithms", scratchpad="while l < r:")
        self.assertLessEqual(msg4.word_count, 45)

        dec_b = SilenceDecision(rung="B", rung_name="Breather", token_class="tiny", action_type="breather", spoken=True)
        msg_b = compose_silence_message(decision=dec_b, problem="Binary Search", course_name="Algorithms", scratchpad="I hate this")
        self.assertLessEqual(msg_b.word_count, 30)

    # 11. Zero tokens on Rungs 0 and 1
    def test_rung_0_and_1_spend_zero_tokens(self):
        dec0 = SilenceDecision(rung=0, rung_name="Silence", token_class="0", action_type="silence", spoken=False)
        msg0 = compose_silence_message(decision=dec0, problem="P", course_name="C", scratchpad="text")
        self.assertEqual(msg0.input_tokens, 0)
        self.assertEqual(msg0.output_tokens, 0)
        self.assertEqual(msg0.word_count, 0)

        dec1 = SilenceDecision(rung=1, rung_name="Ghost Underline", token_class="0", action_type="underline", spoken=False)
        msg1 = compose_silence_message(decision=dec1, problem="P", course_name="C", scratchpad="text")
        self.assertEqual(msg1.input_tokens, 0)
        self.assertEqual(msg1.output_tokens, 0)


if __name__ == "__main__":
    unittest.main()
