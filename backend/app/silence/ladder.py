"""
Escalation Ladder & Silence Policy (Pure Python).

The core philosophy of the Silence Engine:
  "The tutor that watched you struggle for 4 minutes and said 9 words."

Rungs:
  0: Silence          (eye icon stays calm, 0 tokens)
  1: Ghost underline  (suspect line is softly underlined, no words, 0 tokens)
  2: Margin question  (ONE Socratic question <= 15 words in margin, tiny tokens)
  3: Margin hint      (one hint, <= 30 words, never the answer, small tokens)
  4: One step         (reveal exactly the next step only <= 45 words, small tokens)
  B: Breather         (calm 1-2 sentence human reassurance when frustration is high, tiny tokens)

Pure Python rules:
  1. Productive-Struggle Shield: P(productive_struggle) >= shield -> Force Rung 0.
  2. Hysteresis: Trigger must persist across N consecutive ticks (default 3) before escalating.
  3. Cooldown: Minimum elapsed time since last spoken intervention (expands with each intervention).
  4. Spoken Budget: Hard cap on spoken interventions per problem (default 4).
  5. No Rung Skipping: Progressively climb 0 -> 1 -> 2 -> 3 -> 4, unless explicit help_request jumps to 3.
  6. Frustration Precedence: Frustration >= threshold -> Breather first, never dump academic hints on a stressed student.
  7. Finished State: Silence, then a single non-intrusive 'check your answer?' invitation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.silence.signals import TickSignals

RUNG_NAMES = {
    0: "Silence",
    1: "Ghost Underline",
    2: "Margin Question",
    3: "Margin Hint",
    4: "One Step",
    "B": "Breather",
}

TOKEN_CLASSES = {
    0: "0",
    1: "0",
    2: "tiny",
    3: "small",
    4: "small",
    "B": "tiny",
}


@dataclass
class SilenceDecision:
    rung: Union[int, str]                       # 0, 1, 2, 3, 4, or 'B'
    rung_name: str
    token_class: str                            # '0' | 'tiny' | 'small'
    held_back_by: Optional[str] = None          # Reason why tutor stayed silent or held at rung
    probabilities: Dict[str, float] = field(default_factory=dict)
    suspect_lines: List[int] = field(default_factory=list)
    action_type: str = "silence"                # 'silence' | 'underline' | 'question' | 'hint' | 'step' | 'breather' | 'check_answer'
    spoken: bool = False                        # True if LLM generates spoken text (rung >= 2 or 'B')
    latency_ms: float = 0.0
    decider_mode: str = "model"                 # 'model' | 'fallback' | 'unavailable' | 'skipped'
    suggested_prompt_type: Optional[str] = None # For speak.py
    target_misconception_id: Optional[str] = None
    target_misconception_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rung": self.rung,
            "rung_name": self.rung_name,
            "token_class": self.token_class,
            "held_back_by": self.held_back_by,
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "suspect_lines": self.suspect_lines,
            "action_type": self.action_type,
            "spoken": self.spoken,
            "latency_ms": round(self.latency_ms, 1),
            "decider_mode": self.decider_mode,
            "suggested_prompt_type": self.suggested_prompt_type,
            "target_misconception_id": self.target_misconception_id,
            "target_misconception_name": self.target_misconception_name,
        }


# --------------------------------------------------------------------------- #
# Pure Policy Functions                                                       #
# --------------------------------------------------------------------------- #
def check_productive_struggle_shield(
    p_struggle: float,
    shield_threshold: float,
) -> Tuple[bool, Optional[str]]:
    """Rule 1: If student is engaged in productive struggle, protect their flow."""
    if p_struggle >= shield_threshold:
        return True, f"productive_struggle_shield ({p_struggle:.2f} >= {shield_threshold:.2f})"
    return False, None


def check_cooldown(
    seconds_since_last_spoken: float,
    interventions_count: int,
    base_cooldown: float = 20.0,
    cooldown_step: float = 8.0,
) -> Tuple[bool, Optional[str]]:
    """Rule 3: Enforce pacing cooldown between spoken interventions."""
    required = base_cooldown + (interventions_count * cooldown_step)
    if seconds_since_last_spoken < required:
        return True, f"cooldown_active ({seconds_since_last_spoken:.1f}s < {required:.1f}s required)"
    return False, None


def check_budget_exhausted(
    interventions_count: int,
    max_budget: int = 4,
    help_requested: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Rule 4: Spoken budget hard cap. Only explicit help requests can bypass."""
    if interventions_count >= max_budget and not help_requested:
        return True, f"budget_exhausted ({interventions_count}/{max_budget} spoken interventions used)"
    return False, None


def evaluate_escalation_ladder(
    *,
    signals: TickSignals,
    current_rung: int,
    trigger_streak: int,
    seconds_since_last_spoken: float,
    interventions_count: int,
    patience_dial: float = 0.5,  # 0.0 (interrupt less) to 1.0 (interrupt more)
    shield_threshold: float = 0.60,
    frustration_threshold: float = 0.70,
    help_threshold: float = 0.65,
    stuck_threshold: float = 0.60,
    hysteresis_ticks: int = 3,
    max_budget: int = 4,
    finished_prompted: bool = False,
) -> SilenceDecision:
    """
    Evaluates current tick signals and determines the next rung.
    All control flow is pure, deterministic Python.
    """
    if signals.skipped:
        return SilenceDecision(
            rung=current_rung,
            rung_name=RUNG_NAMES.get(current_rung, "Silence"),
            token_class=TOKEN_CLASSES.get(current_rung, "0"),
            held_back_by=f"skipped ({signals.skipped_reason})",
            decider_mode="skipped",
            spoken=False,
        )

    # Shift thresholds based on patience dial:
    # dial = 0.0 -> patience high -> higher thresholds to interrupt (interrupt less)
    # dial = 1.0 -> patience low -> lower thresholds to interrupt (interrupt more)
    dial_offset = (0.5 - patience_dial) * 0.20
    effective_shield = max(0.30, min(0.90, shield_threshold + dial_offset))
    effective_frust = max(0.35, min(0.95, frustration_threshold - dial_offset))
    effective_help = max(0.35, min(0.90, help_threshold - dial_offset))
    effective_stuck = max(0.35, min(0.90, stuck_threshold - dial_offset))

    # Collect probabilities
    p_struggle = float(signals.productive_struggle.measure if signals.productive_struggle else 0.5)
    p_frust = float(signals.frustration.measure if signals.frustration else 0.1)
    p_help = float(signals.help_request.measure if signals.help_request else 0.05)
    
    prog_label = signals.progress.label if signals.progress else "none_of_these"
    prog_probs = signals.progress.probabilities if signals.progress else {}
    p_stuck = max(prog_probs.get("blank_stuck", 0.0), prog_probs.get("wrong_path", 0.0), prog_probs.get("circling", 0.0))

    probs_summary = {
        "productive_struggle": p_struggle,
        "frustration": p_frust,
        "help_request": p_help,
        "stuck": p_stuck,
    }

    suspect_lines = [idx for idx, d in signals.line_suspects.items() if d.triggered]
    misc_id = signals.misconception.label if (signals.misconception and signals.misconception.triggered) else None

    # Priority A: Finished state
    if prog_label == "finished":
        if not finished_prompted:
            return SilenceDecision(
                rung=0,
                rung_name="Silence",
                token_class="0",
                held_back_by="finished_invitation",
                probabilities=probs_summary,
                action_type="check_answer",
                spoken=False,
                latency_ms=signals.latency_ms,
                decider_mode=signals.decider_mode,
            )
        return SilenceDecision(
            rung=0,
            rung_name="Silence",
            token_class="0",
            held_back_by="finished_verified",
            probabilities=probs_summary,
            action_type="silence",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    # Priority B: Frustration Precedence -> Breather First
    if p_frust >= effective_frust:
        is_cooldown, reason = check_cooldown(seconds_since_last_spoken, interventions_count, base_cooldown=15.0)
        if is_cooldown:
            return SilenceDecision(
                rung=0,
                rung_name="Silence",
                token_class="0",
                held_back_by=f"frustration_detected_but_{reason}",
                probabilities=probs_summary,
                action_type="silence",
                latency_ms=signals.latency_ms,
                decider_mode=signals.decider_mode,
            )
        return SilenceDecision(
            rung="B",
            rung_name="Breather",
            token_class="tiny",
            held_back_by=None,
            probabilities=probs_summary,
            action_type="breather",
            spoken=True,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
            suggested_prompt_type="breather",
        )

    # Priority C: Explicit Help Request -> Jump directly to Rung 3 (Margin Hint)
    if p_help >= effective_help:
        return SilenceDecision(
            rung=3,
            rung_name="Margin Hint",
            token_class="small",
            held_back_by=None,
            probabilities=probs_summary,
            suspect_lines=suspect_lines,
            action_type="hint",
            spoken=True,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
            suggested_prompt_type="hint",
            target_misconception_id=misc_id,
        )

    # Priority D: Productive Struggle Shield
    shielded, shield_reason = check_productive_struggle_shield(p_struggle, effective_shield)
    if shielded:
        return SilenceDecision(
            rung=0,
            rung_name="Silence",
            token_class="0",
            held_back_by=shield_reason,
            probabilities=probs_summary,
            suspect_lines=suspect_lines,
            action_type="silence",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    # Priority E: Is student drifting / stuck?
    is_struggling_or_wrong = (
        prog_label in ("wrong_path", "blank_stuck", "circling")
        or p_stuck >= effective_stuck
        or bool(suspect_lines)
        or bool(misc_id)
    )

    if not is_struggling_or_wrong:
        # Student making clear progress or normal writing
        return SilenceDecision(
            rung=0,
            rung_name="Silence",
            token_class="0",
            held_back_by="making_reasoned_progress",
            probabilities=probs_summary,
            action_type="silence",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    # Priority F: Hysteresis check before stepping up rung
    # Need consistent trigger over N consecutive ticks
    target_next_rung = min(4, current_rung + 1 if current_rung > 0 else 1)

    if trigger_streak < hysteresis_ticks:
        return SilenceDecision(
            rung=current_rung,
            rung_name=RUNG_NAMES.get(current_rung, "Silence"),
            token_class=TOKEN_CLASSES.get(current_rung, "0"),
            held_back_by=f"hysteresis_filter ({trigger_streak}/{hysteresis_ticks} ticks trigger streak)",
            probabilities=probs_summary,
            suspect_lines=suspect_lines,
            action_type="underline" if current_rung == 1 else "silence",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    # Rung 1: Ghost Underline (Zero Words, Zero LLM tokens)
    if target_next_rung == 1:
        return SilenceDecision(
            rung=1,
            rung_name="Ghost Underline",
            token_class="0",
            held_back_by=None,
            probabilities=probs_summary,
            suspect_lines=suspect_lines or [0],
            action_type="underline",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
            target_misconception_id=misc_id,
        )

    # Rungs 2-4: Spoken Interventions (Requires Cooldown & Budget checks)
    is_budget_hit, budget_reason = check_budget_exhausted(interventions_count, max_budget)
    if is_budget_hit:
        return SilenceDecision(
            rung=1,  # fallback to visual underline only
            rung_name="Ghost Underline",
            token_class="0",
            held_back_by=budget_reason,
            probabilities=probs_summary,
            suspect_lines=suspect_lines,
            action_type="underline",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    is_cooldown, cd_reason = check_cooldown(seconds_since_last_spoken, interventions_count)
    if is_cooldown:
        return SilenceDecision(
            rung=current_rung if current_rung in (0, 1) else 1,
            rung_name=RUNG_NAMES.get(current_rung if current_rung in (0, 1) else 1, "Ghost Underline"),
            token_class="0",
            held_back_by=cd_reason,
            probabilities=probs_summary,
            suspect_lines=suspect_lines,
            action_type="underline" if current_rung >= 1 else "silence",
            spoken=False,
            latency_ms=signals.latency_ms,
            decider_mode=signals.decider_mode,
        )

    # Advance to target rung (never skipping: 1 -> 2 -> 3 -> 4)
    action_types = {2: "question", 3: "hint", 4: "step"}
    prompt_types = {2: "socratic_question", 3: "hint", 4: "next_step"}

    return SilenceDecision(
        rung=target_next_rung,
        rung_name=RUNG_NAMES[target_next_rung],
        token_class=TOKEN_CLASSES[target_next_rung],
        held_back_by=None,
        probabilities=probs_summary,
        suspect_lines=suspect_lines,
        action_type=action_types.get(target_next_rung, "question"),
        spoken=True,
        latency_ms=signals.latency_ms,
        decider_mode=signals.decider_mode,
        suggested_prompt_type=prompt_types.get(target_next_rung, "socratic_question"),
        target_misconception_id=misc_id,
    )
