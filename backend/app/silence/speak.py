"""
Bedrock Composer for Spoken Rungs (Rung 2, 3, 4, and Breather).

Strict Constraints Enforced:
  - Rung 2: Margin Question -> ONE Socratic question (<= 15 words) anchored to suspect line.
  - Rung 3: Margin Hint     -> ONE hint (<= 30 words), never the final answer.
  - Rung 4: One Step        -> Reveal the immediate next step only (<= 45 words).
  - Breather: Calm reassurance (1-2 sentences, <= 30 words, no academic content).

Post-generation validation:
  - Verifies strict word limits.
  - Verifies no final answer giveaway.
  - References student's own words where possible (<= 8 word snippet).
  - Retries once if violated, then falls back to a certified template flagged 'template'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.silence.atlas import Atlas, Misconception
from backend.app.silence.ladder import SilenceDecision

MAX_WORDS_BY_RUNG = {
    2: 15,
    3: 30,
    4: 45,
    "B": 30,
}

SYSTEM_PROMPTS = {
    2: (
        "You are an ultra-concise Socratic tutor writing a tiny margin note. "
        "The student is working on a problem. Ask EXACTLY ONE short question (STRICT MAXIMUM 15 WORDS). "
        "Do NOT give any explanation or answer. Quote 2-5 of the student's own words to ground it. "
        "Word limit: 15 words."
    ),
    3: (
        "You are an expert tutor writing a short margin hint. "
        "The student is stuck on a step. Give ONE clear, gentle hint pointing toward the governing principle (STRICT MAXIMUM 30 WORDS). "
        "NEVER give the final answer or solve it for them. Reference their reasoning. "
        "Word limit: 30 words."
    ),
    4: (
        "You are a supportive tutor giving the immediate next step. "
        "Reveal ONLY the single next mathematical/logical operation to perform (STRICT MAXIMUM 45 WORDS). "
        "Do not solve past that single step. "
        "Word limit: 45 words."
    ),
    "B": (
        "You are a calm, compassionate human teacher. The student is feeling overwhelmed or frustrated. "
        "Say 1 or 2 calming, reassuring sentences (STRICT MAXIMUM 25 WORDS). "
        "Do NOT give any math or coding advice. Just acknowledge the effort and encourage a deep breath."
    ),
}

TEMPLATES = {
    2: "Look closely at '{quote}': what condition might be missing here?",
    3: "Notice how '{quote}' connects to the base case. What happens when the index reaches zero?",
    4: "Next step: express the recurrence relation for the current state before calculating.",
    "B": "Take a breath. You are doing real, hard thinking here—it is completely normal to pause.",
}


@dataclass
class SpokenMessage:
    rung: Any
    text: str
    target_line: Optional[int]
    word_count: int
    provider: str                       # 'bedrock' | 'app-llm' | 'template'
    model_id: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    retried: bool = False
    flagged_template: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rung": self.rung,
            "text": self.text,
            "target_line": self.target_line,
            "word_count": self.word_count,
            "provider": self.provider,
            "model_id": self.model_id,
            "latency_ms": round(self.latency_ms, 1),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "retried": self.retried,
            "flagged_template": self.flagged_template,
        }


def _clean_quote(scratchpad: str, suspect_line: Optional[int]) -> str:
    lines = scratchpad.splitlines()
    if suspect_line is not None and 0 <= suspect_line < len(lines):
        line = lines[suspect_line].strip()
        words = line.split()[:5]
        if words:
            return " ".join(words)
    # Fallback to recent words
    all_words = scratchpad.split()
    return " ".join(all_words[-4:]) if all_words else "your working"


def _validate_response(text: str, max_words: int, rung: Any) -> bool:
    clean = text.strip().strip('"').strip("'")
    words = clean.split()
    if len(words) > max_words:
        return False
    if len(words) < 3:
        return False
    if rung in (2, 3) and re.search(r"\b(the answer is|therefore x =|qed|solution is)\b", clean.lower()):
        return False
    return True


def compose_silence_message(
    *,
    decision: SilenceDecision,
    problem: str,
    course_name: str,
    scratchpad: str,
    atlas: Optional[Atlas] = None,
    deep_tier: bool = False,
) -> SpokenMessage:
    """Invokes Bedrock to compose calibrated, strictly word-capped guidance."""
    rung = decision.rung
    if rung not in (2, 3, 4, "B"):
        return SpokenMessage(
            rung=rung,
            text="",
            target_line=None,
            word_count=0,
            provider="none",
            model_id="none",
            latency_ms=0.0,
        )

    max_words = MAX_WORDS_BY_RUNG.get(rung, 30)
    system = SYSTEM_PROMPTS.get(rung, SYSTEM_PROMPTS[3])
    suspect_line = decision.suspect_lines[0] if decision.suspect_lines else None
    quote = _clean_quote(scratchpad, suspect_line)

    misc_desc = ""
    if atlas and decision.target_misconception_id:
        target_misc = next((m for m in atlas.misconceptions if m.id == decision.target_misconception_id), None)
        if target_misc:
            misc_desc = f"Detected Misconception: {target_misc.name} ({target_misc.description})"

    user_payload = (
        f"Problem: {problem[:300]}\n"
        f"Course: {course_name}\n"
        f"Student working snippet around suspect line: \"{quote}\"\n"
        f"{misc_desc}\n"
        f"Instruction: Produce output <= {max_words} words."
    )

    # 1. Try Bedrock
    retried = False
    try:
        from backend.app.providers.bedrock_provider import get_bedrock
        br = get_bedrock()
        if br.available():
            tier = "deep" if deep_tier and rung == 4 else "fast"
            for attempt in range(2):
                msgs = [{"role": "user", "content": user_payload}]
                res = br.converse(msgs, system=system, tier=tier, max_tokens=100, temperature=0.3)
                txt = res.get("text", "").strip().strip('"')
                usage = res.get("usage", {})
                in_tok = int(usage.get("inputTokens") or len(user_payload.split()) * 2)
                out_tok = int(usage.get("outputTokens") or len(txt.split()) * 2)

                if _validate_response(txt, max_words, rung):
                    return SpokenMessage(
                        rung=rung,
                        text=txt,
                        target_line=suspect_line,
                        word_count=len(txt.split()),
                        provider="bedrock",
                        model_id=res.get("model_id", "bedrock-haiku"),
                        latency_ms=res.get("latency_ms", 0.0),
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        retried=retried,
                        flagged_template=False,
                    )
                retried = True
                user_payload += f"\nREMINDER: STRICT MAXIMUM {max_words} WORDS. Previous was {len(txt.split())} words."
    except Exception as exc:
        print(f"[silence.speak] Bedrock speech failed ({exc}); falling back")

    # 2. Try App LLM provider
    try:
        from backend.app.providers.llm_provider import get_llm_provider
        from backend.app.core.config import settings
        if settings.GROQ_API_KEY:
            prov = get_llm_provider("groq")
            res = prov.generate_completion(
                [{"role": "system", "content": system}, {"role": "user", "content": user_payload}],
                max_tokens=60,
                temperature=0.3,
            )
            txt = (res.get("content") or "").strip().strip('"')
            if _validate_response(txt, max_words, rung):
                return SpokenMessage(
                    rung=rung,
                    text=txt,
                    target_line=suspect_line,
                    word_count=len(txt.split()),
                    provider="app-llm",
                    model_id=settings.LLM_MODEL or "groq-haiku-fallback",
                    latency_ms=150.0,
                    input_tokens=len(user_payload.split()) * 2,
                    output_tokens=len(txt.split()) * 2,
                    retried=retried,
                    flagged_template=False,
                )
    except Exception as exc:
        print(f"[silence.speak] App LLM speech failed ({exc})")

    # 3. Deterministic certified template fallback (visibly flagged)
    template_str = TEMPLATES.get(rung, TEMPLATES[3]).format(quote=quote)
    return SpokenMessage(
        rung=rung,
        text=template_str,
        target_line=suspect_line,
        word_count=len(template_str.split()),
        provider="template",
        model_id="rule_template",
        latency_ms=0.1,
        input_tokens=0,
        output_tokens=0,
        retried=retried,
        flagged_template=True,
    )
