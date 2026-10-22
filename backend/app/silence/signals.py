"""
Per-tick signals for Strands Decider 2B.
ONE round trip per tick: state is encoded once and evaluated across:
  - progress            (choice: moving_forward | circling | blank_stuck | wrong_path | finished | none_of_these)
  - misconception       (choice: one option per Atlas misconception + none_of_these)
  - productive_struggle (noul: is the student making a real, reasoned attempt?)
  - frustration         (noul: does student text show frustration / giving up?)
  - help_request        (noul: did student explicitly ask for help?)
  - line_suspect_i      (noul x <= 4: does changed line i contain detected misconception?)

Skip the whole tick cheaply if nothing changed since the last tick (or if text is entirely whitespace).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from backend.app.decider import patterns as P
from backend.app.decider.client import (
    Answer,
    AskResult,
    DeciderClient,
    choice as q_choice,
    noul as q_noul,
)
from backend.app.silence.atlas import Atlas, Misconception


@dataclass
class KeystrokeMeta:
    seconds_since_last_keystroke: float = 0.0
    longest_recent_pause: float = 0.0
    delete_rewrite_ratio: float = 0.0
    seconds_since_last_intervention: float = 999.0
    interventions_count: int = 0
    rung_history: List[int] = field(default_factory=list)
    changed_line_indices: List[int] = field(default_factory=list)


@dataclass
class TickSignals:
    skipped: bool = False
    skipped_reason: Optional[str] = None
    state: str = ""
    progress: Optional[P.Decision] = None
    misconception: Optional[P.Decision] = None
    productive_struggle: Optional[P.Decision] = None
    frustration: Optional[P.Decision] = None
    help_request: Optional[P.Decision] = None
    line_suspects: Dict[int, P.Decision] = field(default_factory=dict)
    raw_answers: Dict[str, Answer] = field(default_factory=dict)
    latency_ms: float = 0.0
    decider_mode: str = "model"
    input_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skipped": self.skipped,
            "skipped_reason": self.skipped_reason,
            "latency_ms": round(self.latency_ms, 1),
            "decider_mode": self.decider_mode,
            "progress": self.progress.to_dict() if self.progress else None,
            "misconception": self.misconception.to_dict() if self.misconception else None,
            "productive_struggle": self.productive_struggle.to_dict() if self.productive_struggle else None,
            "frustration": self.frustration.to_dict() if self.frustration else None,
            "help_request": self.help_request.to_dict() if self.help_request else None,
            "line_suspects": {str(k): v.to_dict() for k, v in self.line_suspects.items()},
        }


def build_silence_state(
    *,
    problem: str,
    course_name: str,
    scratchpad: str,
    diff: str,
    meta: KeystrokeMeta,
    weak_concepts: Sequence[str] = (),
) -> str:
    """Serializes problem context and student-only scratchpad state for Decider 2B."""
    pad_lines = scratchpad.splitlines()
    numbered_pad = "\n".join(f"{i+1:2d} | {line}" for i, line in enumerate(pad_lines[:40]))
    weak_txt = ", ".join(list(weak_concepts)[:6]) or "none"
    rungs_txt = " -> ".join(f"R{r}" for r in meta.rung_history[-5:]) or "none"

    return (
        f"--- PROBLEM ---\n{problem.strip()[:800]}\n"
        f"Course: {course_name} | Weak concepts: {weak_txt}\n\n"
        f"--- STUDENT LIVE SCRATCHPAD ---\n{numbered_pad or '(empty scratchpad)'}\n\n"
        f"--- RECENT DIFF ---\n{diff.strip()[:400] or '(no diff)'}\n\n"
        f"--- INTERACTION DYNAMICS ---\n"
        f"Idle pause: {meta.seconds_since_last_keystroke:.1f}s | Longest pause: {meta.longest_recent_pause:.1f}s\n"
        f"Delete/rewrite ratio: {meta.delete_rewrite_ratio:.2f}\n"
        f"Time since last intervention: {meta.seconds_since_last_intervention:.1f}s\n"
        f"Interventions so far: {meta.interventions_count} | Rung history: {rungs_txt}"
    )


# --------------------------------------------------------------------------- #
# Heuristics for offline fallback (clearly labelled, never presented as model) #
# --------------------------------------------------------------------------- #
def _progress_heuristic(state: str, pad: str) -> Dict[str, float]:
    low = pad.lower()
    score = {
        "moving_forward": 0.25,
        "circling": 0.15,
        "blank_stuck": 0.10,
        "wrong_path": 0.20,
        "finished": 0.10,
        "none_of_these": 0.20,
    }
    if not pad.strip():
        score["blank_stuck"] = 0.85
    elif re.search(r"\b(qed|done|answer is|final result|return|conclude)\b", low):
        score["finished"] = 0.75
    elif re.search(r"\b(wait no|stuck|lost|wrong|confused|undo)\b", low):
        score["wrong_path"] = 0.65
    elif len(pad.split()) > 20:
        score["moving_forward"] = 0.60

    tot = sum(score.values()) or 1.0
    return {k: v / tot for k, v in score.items()}


def _noul_heuristics(pad: str, meta: KeystrokeMeta) -> Dict[str, float]:
    low = pad.lower()
    # productive struggle: student is writing reasoning, equations, steps
    words = len(pad.split())
    has_steps = bool(re.search(r"[0-9+\-*/=<>#\n]|step|let|then|if|for|while", low))
    struggle_p = 0.70 if (words >= 8 and has_steps) else (0.45 if words >= 3 else 0.15)

    # frustration
    frust_words = ("hate", "stuck", "give up", "i can't", "cant do this", "impossible", "quit", "ugh", "wtf", "screw this")
    frust_p = 0.85 if any(w in low for w in frust_words) or meta.delete_rewrite_ratio > 0.65 else 0.10

    # help request
    help_words = ("help", "hint", "how do i", "what next", "tutor", "please explain", "what is wrong", "im stuck")
    help_p = 0.90 if any(w in low for w in help_words) else 0.05

    return {
        "productive_struggle": struggle_p,
        "frustration": frust_p,
        "help_request": help_p,
    }


# --------------------------------------------------------------------------- #
# Signal Evaluator                                                            #
# --------------------------------------------------------------------------- #
class SilenceSignalsEvaluator:
    def __init__(self, client: DeciderClient) -> None:
        self.client = client

    def evaluate_tick(
        self,
        *,
        problem: str,
        course_name: str,
        scratchpad: str,
        last_scratchpad: str,
        meta: KeystrokeMeta,
        atlas: Optional[Atlas] = None,
        weak_concepts: Sequence[str] = (),
        thresholds: Optional[Callable[[str], float]] = None,
    ) -> TickSignals:
        get_thr = thresholds or (lambda k: 0.50)

        # 1. Skip check: if identical to last tick and not a heartbeat idle event
        clean_curr = scratchpad.strip()
        clean_last = last_scratchpad.strip()
        diff = ""
        if clean_curr == clean_last and meta.seconds_since_last_keystroke < 3.0:
            return TickSignals(skipped=True, skipped_reason="no_change")

        # Compute diff description
        if clean_curr != clean_last:
            diff = f"+ {clean_curr[len(clean_last):]}" if len(clean_curr) > len(clean_last) else f"Modified {abs(len(clean_curr) - len(clean_last))} chars"
        else:
            diff = f"Idle pause for {meta.seconds_since_last_keystroke:.1f}s"

        state = build_silence_state(
            problem=problem,
            course_name=course_name,
            scratchpad=scratchpad,
            diff=diff,
            meta=meta,
            weak_concepts=weak_concepts,
        )

        # 2. Build questions
        questions: Dict[str, Dict[str, Any]] = {}
        fallbacks: Dict[str, Callable[[str], Dict[str, Any]]] = {}

        # Question: progress
        milestone_hints = " -> ".join(atlas.milestones[:3]) if atlas else "solve the problem correctly"
        progress_options = {
            "moving_forward": f"student is executing a logical sequence towards {milestone_hints}",
            "circling": "student is rewriting, deleting, or rephrasing the same thought without advancing",
            "blank_stuck": "scratchpad is blank, paused with incomplete sentence, or showing no active thought",
            "wrong_path": "student is pursuing a mathematically or conceptually incorrect trajectory",
            "finished": "student has reached a complete, final answer or conclusion",
            "none_of_these": "does not fit any of the progress descriptions above",
        }
        questions["progress"] = q_choice(
            "What is the student's current working progress on this problem?",
            progress_options,
        )
        fallbacks["progress"] = lambda st: {"choice": "moving_forward", "probabilities": _progress_heuristic(st, scratchpad)}

        # Question: misconception (if Atlas exists)
        if atlas and atlas.misconceptions:
            misc_options = {m.id: f"{m.name}: {m.description}" for m in atlas.misconceptions}
            misc_options["none_of_these"] = "student text does not show any of the misconceptions listed"
            questions["misconception"] = q_choice(
                "Does the student's text reflect any of these specific misconceptions?",
                misc_options,
            )
            def _misc_fallback(st: str) -> Dict[str, Any]:
                opts = list(atlas.misconceptions)
                raw = {m.id: 0.1 for m in opts}
                raw["none_of_these"] = 0.5
                tot = sum(raw.values())
                probs = {k: v / tot for k, v in raw.items()}
                return {"choice": "none_of_these", "probabilities": probs}
            fallbacks["misconception"] = _misc_fallback

        # Question: productive_struggle
        questions["productive_struggle"] = q_noul(
            "Is the student making a real, reasoned attempt, even if not yet correct?",
            true="student is actively reasoning, attempting equations, or drafting concrete logic",
            false="student is random guessing, completely blank, or not engaging reasoned thought",
        )
        fallbacks["productive_struggle"] = lambda st: {"noul": _noul_heuristics(scratchpad, meta)["productive_struggle"]}

        # Question: frustration
        questions["frustration"] = q_noul(
            "Does the student's latest text show frustration or wanting to quit?",
            true="student uses angry/resigned language, repeated aggressive deletions, or asks to quit",
            false="student remains calm and focused on problem solving",
        )
        fallbacks["frustration"] = lambda st: {"noul": _noul_heuristics(scratchpad, meta)["frustration"]}

        # Question: help_request
        questions["help_request"] = q_noul(
            "Did the student explicitly ask for help or say they don't know?",
            true="student typed a direct question to the tutor or explicitly states they are stuck",
            false="student is talking to themselves, taking notes, or working independently",
        )
        fallbacks["help_request"] = lambda st: {"noul": _noul_heuristics(scratchpad, meta)["help_request"]}

        # Question: line_suspect_i for changed lines (up to 4)
        lines = scratchpad.splitlines()
        suspect_indices = [idx for idx in meta.changed_line_indices if 0 <= idx < len(lines)][:4]
        if not suspect_indices and lines:
            # Check last 1-2 non-empty lines
            non_empty = [i for i, l in enumerate(lines) if l.strip()]
            suspect_indices = non_empty[-2:]

        if atlas and atlas.misconceptions and suspect_indices:
            top_misc = atlas.misconceptions[0]
            for idx in suspect_indices:
                line_text = lines[idx].strip()
                if line_text:
                    q_key = f"line_suspect_{idx}"
                    questions[q_key] = q_noul(
                        f"Does line {idx+1} ('{line_text[:80]}') contain the misconception '{top_misc.name}'?",
                        true=f"line {idx+1} directly embodies {top_misc.description}",
                        false=f"line {idx+1} does not exhibit {top_misc.name}",
                    )
                    fallbacks[q_key] = lambda st: {"noul": 0.2}

        # 3. Call DeciderClient in ONE round trip
        ask_res: AskResult = self.client.ask(state, questions, fallbacks)

        # 4. Parse Decisions
        def _make_choice_decision(k: str, p_key: str, thr_key: str) -> Optional[P.Decision]:
            ans = ask_res.answers.get(k)
            if not ans:
                return None
            thr = get_thr(thr_key)
            label = ans.choice or "none_of_these"
            trusted = ans.confidence >= thr and label != "none_of_these"
            return P.Decision(
                key=k,
                pattern=p_key,
                kind="choice",
                label=label,
                measure=ans.confidence,
                threshold=thr,
                threshold_key=thr_key,
                triggered=trusted,
                confidence=ans.confidence,
                probabilities=ans.probabilities,
                fallback=ans.fallback,
            )

        def _make_noul_decision(k: str, thr_key: str) -> Optional[P.Decision]:
            ans = ask_res.answers.get(k)
            if not ans:
                return None
            thr = get_thr(thr_key)
            p = float(ans.p_true if ans.p_true is not None else 0.5)
            triggered = p >= thr
            return P.Decision(
                key=k,
                pattern=k,
                kind="noul",
                label="yes" if p >= 0.5 else "no",
                measure=p,
                threshold=thr,
                threshold_key=thr_key,
                triggered=triggered,
                confidence=max(p, 1 - p),
                probabilities={"yes": p, "no": 1 - p},
                fallback=ans.fallback,
            )

        progress_dec = _make_choice_decision("progress", "progress_pattern", "silence_progress")
        misc_dec = _make_choice_decision("misconception", "misconception_pattern", "silence_misconception")
        struggle_dec = _make_noul_decision("productive_struggle", "silence_shield")
        frust_dec = _make_noul_decision("frustration", "silence_frustration")
        help_dec = _make_noul_decision("help_request", "silence_help")

        suspect_decs: Dict[int, P.Decision] = {}
        for idx in suspect_indices:
            q_key = f"line_suspect_{idx}"
            d = _make_noul_decision(q_key, "silence_suspect")
            if d:
                suspect_decs[idx] = d

        return TickSignals(
            skipped=False,
            state=state,
            progress=progress_dec,
            misconception=misc_dec,
            productive_struggle=struggle_dec,
            frustration=frust_dec,
            help_request=help_dec,
            line_suspects=suspect_decs,
            raw_answers=ask_res.answers,
            latency_ms=ask_res.latency_ms,
            decider_mode=ask_res.mode,
            input_tokens=ask_res.input_tokens,
        )
