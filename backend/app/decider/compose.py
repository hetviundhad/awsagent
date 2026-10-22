"""
Text the gate needs when it does NOT run the normal RAG answer
(clarifying question, friendly redirect, supportive reply).

The Decider decided WHAT to do; Bedrock writes the words. If Bedrock is down we fall back to the app's
existing provider, then to a deterministic template - the student always gets a sensible reply.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

PROMPTS = {
    "clarify": ("You are a tutor. The student's message is too vague to answer well. Ask ONE short, friendly clarifying "
                "question that offers 2-3 concrete options drawn from the course topics. No lecture. Max 3 sentences."),
    "redirect": ("You are a friendly study tutor. The student asked something unrelated to their course. Reply in 2-3 "
                 "sentences: acknowledge lightly, say you're focused on the course, and suggest 2 specific things you can help with "
                 "from the course topics."),
    "support": ("You are a kind, steady study coach. The student sounds stressed or overwhelmed. In 4-5 sentences: validate the "
                "feeling without drama, suggest ONE tiny next step (10 minutes), and offer to build a small plan or a gentle quiz. "
                "If they mention self-harm or crisis, encourage contacting local emergency services or a trusted person."),
}

TEMPLATES = {
    "clarify": "I want to get this right - could you tell me a bit more about what you'd like help with? For example: {opts}?",
    "redirect": "That's a bit outside what I can help with here - I'm focused on **{course}**. I can help with {opts}. Want to start with one of those?",
    "support": ("That sounds like a lot, and it's okay to feel that way. Let's make it small: pick one topic from **{course}** and "
                "spend just 10 focused minutes on it. I can explain it simply or quiz you gently - which would feel better right now?"),
}


def compose(kind: str, message: str, course_name: str, topics: Sequence[str], history: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Returns {'text', 'generated_by'}."""
    topics = [t for t in topics if t][:3] or ["the main concepts"]
    opts = ", ".join(topics)
    user = (f"Course: {course_name}\nCourse topics: {', '.join(topics)}\nStudent said: {message[:600]}")
    # 1) Bedrock
    try:
        from backend.app.providers.bedrock_provider import get_bedrock, BedrockUnavailable
        br = get_bedrock()
        if br.available():
            msgs = [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in (history or [])[-4:]]
            msgs.append({"role": "user", "content": user})
            out = br.converse(msgs, system=PROMPTS[kind], tier="fast", max_tokens=300, temperature=0.5)
            return {"text": out["text"], "generated_by": {"provider": "bedrock", "model_id": out["model_id"],
                                                         "latency_ms": round(out["latency_ms"], 1)}}
    except Exception as exc:  # noqa: BLE001
        print(f"[compose] Bedrock unavailable ({exc}); trying app provider")
    # 2) existing provider (Groq/OpenAI)
    try:
        from backend.app.providers.llm_provider import get_llm_provider
        from backend.app.core.config import settings
        prov = get_llm_provider("groq" if settings.GROQ_API_KEY else settings.LLM_PROVIDER)
        res = prov.generate_completion([{"role": "system", "content": PROMPTS[kind]}, {"role": "user", "content": user}],
                                       max_tokens=300, temperature=0.5)
        if res.get("content"):
            return {"text": res["content"], "generated_by": {"provider": "app-llm"}}
    except Exception as exc:  # noqa: BLE001
        print(f"[compose] app provider unavailable ({exc}); using template")
    # 3) template
    return {"text": TEMPLATES[kind].format(opts=opts, course=course_name), "generated_by": {"provider": "template"}}
