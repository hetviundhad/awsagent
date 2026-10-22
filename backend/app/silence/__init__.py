"""
StudyMind Silence Engine
========================
"The AI tutor that knows when to SHUT UP"
Tagline: "The tutor that watched you struggle for 4 minutes and said 9 words."

Public API:
  - atlas: Misconception Atlas (Bedrock, once per problem)
  - signals: typed Decider 2B questions per tick
  - ladder: escalation ladder + silence policy (pure Python)
  - speak: word-capped Bedrock margin guidance
  - session: per-session state, concurrency, latest-wins
  - replay: full tick timeline for Time Machine
  - baseline: Always-Talk baseline for empirical comparison
"""
from .atlas import Atlas, Misconception, build_atlas
from .baseline import run_always_talk_baseline
from .ladder import SilenceDecision, evaluate_escalation_ladder
from .replay import ReplayStore, SessionRecord, TickRecord, get_replay_store
from .session import SilenceSession, SilenceSessionManager, get_silence_manager
from .signals import KeystrokeMeta, SilenceSignalsEvaluator, TickSignals
from .speak import SpokenMessage, compose_silence_message

__all__ = [
    "Atlas",
    "Misconception",
    "build_atlas",
    "SilenceDecision",
    "evaluate_escalation_ladder",
    "KeystrokeMeta",
    "SilenceSignalsEvaluator",
    "TickSignals",
    "SpokenMessage",
    "compose_silence_message",
    "ReplayStore",
    "SessionRecord",
    "TickRecord",
    "get_replay_store",
    "run_always_talk_baseline",
    "SilenceSession",
    "SilenceSessionManager",
    "get_silence_manager",
]
