"""
StudyMind Decision Layer
========================
A thin, dependency-free layer that puts Strands Decider 2B in front of the
StudyMind AI tutor.  The Decider never writes text; it only returns
calibrated probabilities.  Plain Python turns those numbers into actions and
Amazon Bedrock writes whatever text the action requires.

Public surface:
    DeciderClient   - HTTP client for `strands-decider serve` (+ labelled offline fallback)
    patterns        - REUSABLE decision patterns (drop these into any agent)
    ThresholdStore  - confidence thresholds that adapt from student feedback
    StudyGate       - one round-trip gate: policy + clarity + routing + prerequisite gap
"""
from .client import DeciderClient, Answer, get_client          # noqa: F401
from .calibration import ThresholdStore, get_thresholds        # noqa: F401
from .trace import TraceStore, get_traces                      # noqa: F401
