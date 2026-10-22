"""
REUSABLE DECIDER 2B DECISION PATTERNS
=====================================
Copy this file (plus client.py) into ANY agent. A pattern bundles:

    1. the typed question + option set      -> `questions()`
    2. a rule that turns probabilities into  -> `interpret()`   (plain Python - the code decides, not the model)
       a yes/no "triggered" verdict
    3. an offline heuristic (flagged)        -> `fallback()`

Generic building blocks
    PolicyPattern  (choice) - classify a request into a category, map category -> action
    YesNoPattern   (noul)   - one calibrated yes/no, trigger on high or low P

StudyMind factories (the five hackathon patterns, all driven by DYNAMIC data):
    pedagogy_policy(course)        #policy        options/descriptions are built from the live course
    clarity_check()                #policy        "is the message specific enough to answer?"
    complexity_router()            #model-routing small vs frontier Bedrock model
    prereq_gap(weak_concepts)      #context-memory does the question lean on a concept the learner is weak in?
    context_relevance()            #context-memory score a retrieved chunk before injecting it
    grounded_tool_arg(tool,arg,v)  #guardrails    is a tool argument grounded in what the student said?
    tool_selection(tools)          #tool-selection pick which tool to call

Lessons from the community that are baked in:
    * option DESCRIPTIONS change accuracy dramatically (51% -> 90% in one experiment)
    * always include a "none_of_these" option, or the model is forced to guess
    * ask SPECIFIC questions ("did the student name X?") not vague ones ("is it grounded?")
    * do NOT flip questions ("which must NOT...") - the model largely ignores negation
    * show a grounding question only what the USER said, not the agent's own text
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .client import Answer, AskResult, DeciderClient, choice as q_choice, noul as q_noul

NONE_OF_THESE = "none_of_these"


# --------------------------------------------------------------------------- #
# Decision record                                                              #
# --------------------------------------------------------------------------- #
@dataclass
class Decision:
    key: str
    pattern: str
    kind: str
    label: str                       # choice name, or "yes"/"no"
    measure: float                   # the number compared to the threshold
    threshold: float
    threshold_key: str
    triggered: bool                  # did the measure cross the threshold in the pattern's trigger direction?
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    action: Optional[str] = None
    fallback: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key, "pattern": self.pattern, "kind": self.kind, "label": self.label,
            "measure": round(self.measure, 4), "threshold": round(self.threshold, 4),
            "threshold_key": self.threshold_key, "triggered": self.triggered,
            "confidence": round(self.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "action": self.action, "fallback": self.fallback,
        }


# --------------------------------------------------------------------------- #
# Generic patterns                                                             #
# --------------------------------------------------------------------------- #
class Pattern:
    key: str
    name: str

    def question(self) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def fallback(self, state: str) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def interpret(self, ans: Answer, threshold: float) -> Decision:  # pragma: no cover
        raise NotImplementedError


@dataclass
class PolicyPattern(Pattern):
    """(choice) Classify into one of N categories; map each category to an action."""
    key: str
    instructions: str
    options: Dict[str, str]
    actions: Dict[str, str]
    threshold_key: str = "policy"
    name: str = "policy"
    heuristic: Optional[Callable[[str], Dict[str, float]]] = None

    def __post_init__(self) -> None:
        self.options = dict(self.options)
        if NONE_OF_THESE not in self.options:
            self.options[NONE_OF_THESE] = "does not fit any option above"

    def question(self) -> Dict[str, Any]:
        return q_choice(self.instructions, self.options)

    def fallback(self, state: str) -> Dict[str, Any]:
        if self.heuristic:
            probs = self.heuristic(state)
            return {"choice": max(probs, key=probs.get), "probabilities": probs}
        from .client import _lexical_choice
        return _lexical_choice(state, self.options)

    def interpret(self, ans: Answer, threshold: float) -> Decision:
        label = ans.choice or NONE_OF_THESE
        trusted = ans.confidence >= threshold and label != NONE_OF_THESE
        return Decision(self.key, self.name, "choice", label, ans.confidence, threshold, self.threshold_key,
                        trusted, ans.confidence, ans.probabilities,
                        self.actions.get(label) if trusted else None, ans.fallback)


@dataclass
class YesNoPattern(Pattern):
    """(noul) One calibrated yes/no. `trigger_when='high'` fires when P(true) >= threshold, 'low' when P(true) < threshold."""
    key: str
    instructions: str
    true: str
    false: str
    threshold_key: str
    trigger_when: str = "high"
    name: str = "yes_no"
    heuristic: Optional[Callable[[str], float]] = None

    def question(self) -> Dict[str, Any]:
        return q_noul(self.instructions, self.true, self.false)

    def fallback(self, state: str) -> Dict[str, Any]:
        return {"noul": self.heuristic(state) if self.heuristic else 0.5}

    def interpret(self, ans: Answer, threshold: float) -> Decision:
        p = float(ans.p_true if ans.p_true is not None else 0.5)
        triggered = (p >= threshold) if self.trigger_when == "high" else (p < threshold)
        return Decision(self.key, self.name, "noul", "yes" if p >= 0.5 else "no", p, threshold,
                        self.threshold_key, triggered, max(p, 1 - p), {"yes": p, "no": 1 - p},
                        None, ans.fallback)


# --------------------------------------------------------------------------- #
# Runner - ONE round trip for any number of patterns                           #
# --------------------------------------------------------------------------- #
def run_patterns(client: DeciderClient, state: str, patterns: Sequence[Pattern],
                 thresholds: Callable[[str], float]) -> tuple[Dict[str, Decision], AskResult]:
    """Ask every pattern's question against the SAME state in a single request."""
    questions = {p.key: p.question() for p in patterns}
    fallbacks = {p.key: p.fallback for p in patterns}
    res = client.ask(state, questions, fallbacks)
    out: Dict[str, Decision] = {}
    for p in patterns:
        ans = res.answers.get(p.key)
        if ans is not None:
            out[p.key] = p.interpret(ans, thresholds(p.threshold_key))
    return out, res


# --------------------------------------------------------------------------- #
# State helpers                                                                #
# --------------------------------------------------------------------------- #
def latest_message(state: str) -> str:
    m = re.search(r"--- NEW STUDENT MESSAGE ---\s*(.*)\Z", state, re.S)
    return (m.group(1) if m else state).strip()


def _has(text: str, words: Sequence[str]) -> bool:
    t = text.lower()
    return any(w in t for w in words)


# --------------------------------------------------------------------------- #
# StudyMind factories                                                          #
# --------------------------------------------------------------------------- #
POLICY_ACTIONS = {
    "explain_concept": "answer",
    "worked_example": "answer",
    "course_logistics": "answer",
    "quiz_request": "quiz",
    "homework_answer": "socratic",
    "emotional_support": "support",
    "off_topic": "redirect",
}


def _policy_heuristic(state: str) -> Dict[str, float]:
    m = latest_message(state)
    score = {k: 0.04 for k in POLICY_ACTIONS}
    score[NONE_OF_THESE] = 0.08
    if _has(m, ("quiz me", "test me", "practice question", "give me questions", "mcq")):
        score["quiz_request"] += 1.0
    if _has(m, ("overwhelmed", "stressed", "anxious", "i give up", "can't cope", "panic", "burnt out", "burned out")):
        score["emotional_support"] += 1.0
    if _has(m, ("just give me the answer", "solve this", "do my homework", "answer for q", "write my assignment",
                "what is the answer to question", "give me the solution")):
        score["homework_answer"] += 1.0
    if _has(m, ("syllabus", "what topics", "which chapters", "course cover", "deadline", "exam date")):
        score["course_logistics"] += 1.0
    if _has(m, ("example", "step by step", "code", "walk me through", "analogy", "demonstrate")):
        score["worked_example"] += 0.6
    if _has(m, ("movie", "recipe", "football", "cricket score", "girlfriend", "boyfriend", "joke", "song", "weather", "bitcoin price")):
        score["off_topic"] += 1.0
    if _has(m, ("what is", "explain", "why", "how does", "difference between", "define", "meaning of")):
        score["explain_concept"] += 0.6
    total = sum(score.values())
    return {k: v / total for k, v in score.items()}


def pedagogy_policy(course_name: str = "this course", topics: Sequence[str] = ()) -> PolicyPattern:
    """#policy - what does this student need RIGHT NOW? Option text is built from the live course, so it adapts per course."""
    topic_txt = ", ".join(list(topics)[:8]) or "the uploaded course material"
    return PolicyPattern(
        key="policy",
        instructions="What does the student need from their tutor right now?",
        options={
            "explain_concept": f"the student wants a concept from {course_name} explained or clarified ({topic_txt})",
            "worked_example": "the student asks for an example, code, an analogy or a step-by-step walkthrough of something",
            "quiz_request": "the student asks to be quizzed, tested or given practice questions",
            "homework_answer": "the student pastes an assignment or exam question and just wants the final answer to hand in",
            "course_logistics": "the student asks what the course covers, the syllabus, chapters, deadlines or materials",
            "emotional_support": "the student expresses stress, anxiety, burnout or feeling overwhelmed about studying",
            "off_topic": f"the request is unrelated to {course_name} and to studying (entertainment, chit-chat, news, other subjects)",
        },
        actions=POLICY_ACTIONS, threshold_key="policy", name="policy", heuristic=_policy_heuristic)


def clarity_check() -> YesNoPattern:
    """#policy - if the message is too vague, ASK instead of guessing (Guide-style)."""
    def h(state: str) -> float:
        m = latest_message(state)
        words = re.findall(r"[A-Za-z0-9']+", m)
        vague = _has(m, ("this", "that", "it ", "explain more", "what about")) and len(words) <= 5
        return 0.15 if (len(words) <= 2 or vague) else 0.75
    return YesNoPattern(
        key="clarity",
        instructions="Is the student's NEW message specific enough to answer well without guessing which concept they mean?",
        true="the message names a concept, problem or task clearly, or it clearly follows from the earlier student messages",
        false="the message is too vague or refers to something unnamed (e.g. 'explain it', 'what about that')",
        threshold_key="clarity", trigger_when="low", name="clarity", heuristic=h)


def complexity_router() -> YesNoPattern:
    """#model-routing - frontier/deep Bedrock model only when the question genuinely needs it."""
    def h(state: str) -> float:
        m = latest_message(state)
        s = 0.15
        if len(m.split()) > 28:
            s += 0.30
        if _has(m, ("derive", "prove", "design", "compare", "trade-off", "tradeoff", "complexity of", "optimi",
                    "implement", "why does", "walk through", "analy", "edge case")):
            s += 0.45
        return min(0.9, s)
    return YesNoPattern(
        key="complexity",
        instructions="Does a good answer need multi-step reasoning, a derivation, a code design, or comparing several concepts?",
        true="a correct answer requires several reasoning steps, a derivation, code, or a comparison",
        false="a short definition, recall or single-concept explanation is enough",
        threshold_key="complexity", trigger_when="high", name="model_routing", heuristic=h)


def prereq_gap(weak_concepts: Sequence[str]) -> Optional[YesNoPattern]:
    """#context-memory - uses the learner model: does the question lean on something the student is weak in?"""
    weak = [w for w in weak_concepts if w][:10]
    if not weak:
        return None

    def h(state: str) -> float:
        m = latest_message(state).lower()
        return 0.8 if any(w.lower() in m for w in weak) else 0.2
    return YesNoPattern(
        key="prereq",
        instructions="Does the student's NEW message depend on a concept listed under 'weak concepts' in the student profile?",
        true="the question builds on, or directly involves, one of the weak concepts",
        false="the question is about something else",
        threshold_key="prereq", trigger_when="high", name="prerequisite_gap", heuristic=h)


def context_relevance() -> YesNoPattern:
    """#context-memory - score ONE retrieved chunk before it is injected into the prompt."""
    def h(state: str) -> float:
        q = set(re.findall(r"[a-z0-9]{4,}", state.split("--- EXCERPT ---")[0].lower()))
        e = set(re.findall(r"[a-z0-9]{4,}", state.split("--- EXCERPT ---")[-1].lower()))
        return min(0.95, 0.1 + 2.5 * len(q & e) / (len(q) or 1))
    return YesNoPattern(
        key="relevance",
        instructions="Does the excerpt directly help answer the student's question?",
        true="the excerpt contains information needed to answer the question",
        false="the excerpt is about something else or only loosely related",
        threshold_key="relevance", trigger_when="high", name="context_relevance", heuristic=h)


def grounded_tool_arg(tool: str, arg: str, value: Any) -> YesNoPattern:
    """#guardrails - SPECIFIC question per tool argument, generated at call time (dynamic)."""
    def h(state: str) -> float:
        said = state.split("--- PROPOSED TOOL CALL ---")[0].lower()
        return 0.85 if str(value).lower() in said else 0.2
    return YesNoPattern(
        key=f"grounded_{arg}",
        instructions=f"Did the student mention or clearly ask about '{value}' (the value used for '{arg}' in the call to {tool})?",
        true=f"'{value}' appears in, or is clearly implied by, what the student said",
        false=f"the student never mentioned '{value}'; the agent guessed it",
        threshold_key="grounded", trigger_when="low", name="grounding_guardrail", heuristic=h)


def tool_selection(tools: Mapping[str, str]) -> PolicyPattern:
    """#tool-selection - pick the tool from the student's words; options come from the live tool registry."""
    return PolicyPattern(
        key="tool", instructions="Which tool should the tutor call for this student request?",
        options=dict(tools), actions={k: k for k in tools}, threshold_key="policy", name="tool_selection")


def build_state(*, course: str, topics: Sequence[str], weak: Sequence[str], mastered: Sequence[str],
                locked: Sequence[str], student_history: Sequence[str], message: str) -> str:
    """One shared state, encoded once by the model. Only STUDENT text goes in (never the agent's own words)."""
    hist = "\n".join(f"student: {h[:240]}" for h in student_history[-3:]) or "(no earlier messages)"
    return (
        f"--- COURSE ---\n{course}; topics: {', '.join(list(topics)[:12]) or 'n/a'}\n\n"
        f"--- STUDENT PROFILE ---\nweak concepts: {', '.join(list(weak)[:8]) or 'none'}\n"
        f"mastered concepts: {', '.join(list(mastered)[:8]) or 'none'}\n"
        f"locked concepts: {', '.join(list(locked)[:6]) or 'none'}\n\n"
        f"--- EARLIER STUDENT MESSAGES ---\n{hist}\n\n"
        f"--- NEW STUDENT MESSAGE ---\n{message.strip()[:1200]}"
    )


# --------------------------------------------------------------------------- #
# Reusable #policy Pattern: Proactivity & Silence (The "When to speak?" Recipe) #
# --------------------------------------------------------------------------- #
def silence_signals(task: str = "current task", milestones: Sequence[str] = ()) -> List[Pattern]:
    """#policy - typed Decider 2B pattern bundle for when an assistant should speak vs stay silent."""
    milestone_txt = " -> ".join(list(milestones)[:3]) or "reach the correct solution"
    
    prog_opts = {
        "moving_forward": f"the user is executing a logical sequence towards {milestone_txt}",
        "circling": "the user is rewriting or rephrasing without advancing",
        "blank_stuck": "the user is idle, blank, or showing no active thought",
        "wrong_path": "the user is pursuing a flawed, erroneous trajectory",
        "finished": "the user has completed the task or reached the goal",
        NONE_OF_THESE: "does not match any category above",
    }
    
    return [
        PolicyPattern(
            key="progress",
            instructions="What is the user's current working progress on this task?",
            options=prog_opts,
            actions={"wrong_path": "nudge", "blank_stuck": "hint", "finished": "verify"},
            threshold_key="silence_progress",
            name="progress",
        ),
        YesNoPattern(
            key="productive_struggle",
            instructions="Is the user making a real, reasoned attempt, even if not yet correct?",
            true="the user is actively reasoning, drafting logic, or trying concrete steps",
            false="the user is random guessing, completely blank, or stuck with no idea",
            threshold_key="silence_shield",
            trigger_when="high",
            name="productive_struggle",
        ),
        YesNoPattern(
            key="frustration",
            instructions="Does the user's latest text show frustration or wanting to quit?",
            true="the user expresses irritation, resignation, repeated aggressive deletion, or gives up",
            false="the user remains calm and engaged",
            threshold_key="silence_frustration",
            trigger_when="high",
            name="frustration",
        ),
        YesNoPattern(
            key="help_request",
            instructions="Did the user explicitly ask for help or say they don't know?",
            true="the user directly typed a request for help, a question, or asked what to do next",
            false="the user is thinking out loud, coding, or working independently",
            threshold_key="silence_help",
            trigger_when="high",
            name="help_request",
        ),
    ]


@dataclass
class ProactivityResult:
    action: str                                  # 'silence' | 'nudge' | 'question' | 'hint' | 'step' | 'breather'
    rung: int | str                              # 0, 1, 2, 3, 4, 'B'
    spoken: bool                                 # True if the LLM should speak
    held_back_by: Optional[str] = None           # Why the assistant stayed silent
    probabilities: Dict[str, float] = field(default_factory=dict)
    decisions: Dict[str, Decision] = field(default_factory=dict)
    latency_ms: float = 0.0
    mode: str = "model"


class ProactivityGate:
    """
    Generic, zero-dependency Proactivity Gate.
    Answers: 'Should my AI assistant interrupt this human right now?'

    Encapsulates:
      - Productive Struggle Shield: if user is making reasoned progress, do not interrupt.
      - Hysteresis: requires N consecutive trigger ticks to avoid flicker.
      - Pacing Cooldown: minimum seconds between interruptions.
      - Budget Cap: maximum spoken interventions per task session.
    """
    def __init__(self, client: DeciderClient, thresholds: Optional[Callable[[str], float]] = None,
                 shield: float = 0.60, frustration_thr: float = 0.70, help_thr: float = 0.65,
                 hysteresis_ticks: int = 3, base_cooldown: float = 20.0, max_budget: int = 4) -> None:
        self.client = client
        self.thresholds = thresholds or (lambda k: {"silence_shield": shield, "silence_frustration": frustration_thr,
                                                    "silence_help": help_thr, "silence_progress": 0.50}.get(k, 0.50))
        self.shield = shield
        self.frustration_thr = frustration_thr
        self.help_thr = help_thr
        self.hysteresis_ticks = hysteresis_ticks
        self.base_cooldown = base_cooldown
        self.max_budget = max_budget

        self.current_rung: int = 0
        self.trigger_streak: int = 0
        self.last_spoken_time: float = 0.0
        self.interventions_count: int = 0

    def evaluate(self, state: str, task: str = "task", now: Optional[float] = None) -> ProactivityResult:
        import time
        ts = now or time.time()
        sec_since_spoken = (ts - self.last_spoken_time) if self.last_spoken_time > 0 else 999.0

        pats = silence_signals(task)
        decisions, ask = run_patterns(self.client, state, pats, self.thresholds)

        p_struggle = decisions["productive_struggle"].measure if "productive_struggle" in decisions else 0.5
        p_frust = decisions["frustration"].measure if "frustration" in decisions else 0.1
        p_help = decisions["help_request"].measure if "help_request" in decisions else 0.05
        prog = decisions.get("progress")

        probs = {"productive_struggle": p_struggle, "frustration": p_frust, "help_request": p_help}

        # 1. Frustration Precedence -> Breather
        if p_frust >= self.frustration_thr:
            self.last_spoken_time = ts
            self.interventions_count += 1
            return ProactivityResult(action="breather", rung="B", spoken=True, probabilities=probs,
                                     decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # 2. Explicit Help Request -> Immediate Hint (Rung 3)
        if p_help >= self.help_thr:
            self.last_spoken_time = ts
            self.interventions_count += 1
            self.current_rung = 3
            return ProactivityResult(action="hint", rung=3, spoken=True, probabilities=probs,
                                     decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # 3. Productive Struggle Shield
        if p_struggle >= self.shield:
            self.trigger_streak = max(0, self.trigger_streak - 1)
            return ProactivityResult(action="silence", rung=0, spoken=False,
                                     held_back_by=f"productive_struggle_shield ({p_struggle:.2f} >= {self.shield:.2f})",
                                     probabilities=probs, decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # 4. Trigger check (stuck, wrong path, circling)
        is_trigger = bool(prog and prog.label in ("wrong_path", "blank_stuck", "circling"))
        if is_trigger:
            self.trigger_streak += 1
        else:
            self.trigger_streak = max(0, self.trigger_streak - 1)

        # 5. Hysteresis
        target_rung = min(4, self.current_rung + 1 if self.current_rung > 0 else 1)
        if self.trigger_streak < self.hysteresis_ticks:
            return ProactivityResult(action="silence", rung=self.current_rung, spoken=False,
                                     held_back_by=f"hysteresis_wait ({self.trigger_streak}/{self.hysteresis_ticks} ticks)",
                                     probabilities=probs, decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # 6. Rung 1 (Nudge / Soft Underline - zero words)
        if target_rung == 1:
            self.current_rung = 1
            return ProactivityResult(action="nudge", rung=1, spoken=False, probabilities=probs,
                                     decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # 7. Budget & Cooldown for Spoken Rungs (2-4)
        if self.interventions_count >= self.max_budget:
            return ProactivityResult(action="nudge", rung=1, spoken=False,
                                     held_back_by=f"budget_cap ({self.interventions_count}/{self.max_budget})",
                                     probabilities=probs, decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        required_cd = self.base_cooldown + (self.interventions_count * 8.0)
        if sec_since_spoken < required_cd:
            return ProactivityResult(action="nudge", rung=1, spoken=False,
                                     held_back_by=f"cooldown_active ({sec_since_spoken:.1f}s < {required_cd:.1f}s)",
                                     probabilities=probs, decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

        # Advance to spoken rung
        self.current_rung = target_rung
        self.last_spoken_time = ts
        self.interventions_count += 1
        action_map = {2: "question", 3: "hint", 4: "step"}
        return ProactivityResult(action=action_map.get(target_rung, "question"), rung=target_rung, spoken=True,
                                 probabilities=probs, decisions=decisions, latency_ms=ask.latency_ms, mode=ask.mode)

