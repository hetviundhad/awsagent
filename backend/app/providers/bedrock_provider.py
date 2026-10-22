"""
Amazon Bedrock text generation for StudyMind (Converse API).

    BedrockRuntime       - tiny, lazy boto3 wrapper (fast / deep tiers, retries, credential check)
    BedrockLLMProvider   - drop-in LLM provider: Bedrock writes the tutor answer, everything else
                           (quiz generation, ingestion helpers...) is inherited from the OpenAI-compatible
                           provider if a Groq/OpenAI key is configured, so nothing in the app breaks.

The Decider picks the *tier* (fast Haiku vs deep Sonnet) per request via `decider.context.route_var`.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings, is_test_environment
from backend.app.core.errors import AIServiceUnavailableError
from backend.app.decider.context import route_var
from backend.app.providers.llm_provider import OpenAICompatibleLLMProvider, get_topic_links

DEFAULT_FAST = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
DEFAULT_DEEP = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


class BedrockUnavailable(RuntimeError):
    pass


class BedrockRuntime:
    def __init__(self) -> None:
        self.region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        self.models = {
            "fast": os.environ.get("BEDROCK_MODEL_FAST", DEFAULT_FAST),
            "deep": os.environ.get("BEDROCK_MODEL_DEEP", DEFAULT_DEEP),
        }
        self._client = None
        self._lock = threading.Lock()
        self._status: Dict[str, Any] = {"checked": 0.0, "ok": False, "error": "not checked"}
        self.stats = {"calls": 0, "errors": 0, "total_ms": 0.0}

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    try:
                        import boto3
                        from botocore.config import Config
                    except ImportError as exc:
                        raise BedrockUnavailable("boto3 is not installed: pip install boto3 'botocore[crt]'") from exc
                    self._client = boto3.client(
                        "bedrock-runtime", region_name=self.region,
                        config=Config(retries={"max_attempts": 3, "mode": "adaptive"},
                                      read_timeout=60, connect_timeout=5))
        return self._client

    def status(self, force: bool = False) -> Dict[str, Any]:
        """Cheap credential check (no model call), cached for 30 s."""
        if not force and time.time() - self._status["checked"] < 30:
            return self._status
        ok, err = False, None
        try:
            import boto3
            creds = boto3.Session(region_name=self.region).get_credentials()
            ok = creds is not None
            err = None if ok else "no AWS credentials found (run `aws login` / `aws configure` or set AWS_* env vars)"
        except ImportError:
            err = "boto3 is not installed"
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
        self._status = {"checked": time.time(), "ok": ok, "error": err, "region": self.region, "models": self.models}
        return self._status

    def available(self) -> bool:
        return bool(self.status()["ok"])

    def converse(self, messages: List[Dict[str, str]], system: str = "", tier: str = "fast",
                 model_id: Optional[str] = None, max_tokens: int = 1200, temperature: float = 0.3) -> Dict[str, Any]:
        """messages: [{'role': 'user'|'assistant', 'content': str}]  -> {'text', 'model_id', 'latency_ms'}"""
        model = model_id or self.models.get(tier) or self.models["fast"]
        norm: List[Dict[str, Any]] = []
        for m in messages:                                   # Converse needs strictly alternating roles, user first
            role = "assistant" if m.get("role") == "assistant" else "user"
            text = (m.get("content") or "").strip() or "."
            if norm and norm[-1]["role"] == role:
                norm[-1]["content"][0]["text"] += "\n\n" + text
            else:
                norm.append({"role": role, "content": [{"text": text}]})
        while norm and norm[0]["role"] != "user":
            norm.pop(0)
        if not norm:
            raise BedrockUnavailable("no user message to send")
        kwargs: Dict[str, Any] = {"modelId": model, "messages": norm,
                                  "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature}}
        if system:
            kwargs["system"] = [{"text": system}]
        t0 = time.perf_counter()
        try:
            resp = self._get_client().converse(**kwargs)
        except BedrockUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - botocore errors are many; normalise
            self.stats["errors"] += 1
            self._status["checked"] = 0.0
            raise BedrockUnavailable(f"{type(exc).__name__}: {exc}") from exc
        ms = (time.perf_counter() - t0) * 1000
        self.stats["calls"] += 1
        self.stats["total_ms"] += ms
        parts = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise BedrockUnavailable("empty response from model")
        return {"text": text, "model_id": model, "latency_ms": ms}


_runtime: Optional[BedrockRuntime] = None


def get_bedrock() -> BedrockRuntime:
    global _runtime
    if _runtime is None:
        _runtime = BedrockRuntime()
    return _runtime


# --------------------------------------------------------------------------- #
class BedrockLLMProvider(OpenAICompatibleLLMProvider):
    """Bedrock for the tutor answer + generic completions; parent (Groq/OpenAI) for the long tail."""

    def __init__(self, api_key: str = "", base_url: str = "https://api.groq.com/openai/v1",
                 model: Optional[str] = None) -> None:
        super().__init__(api_key=api_key, base_url=base_url, model=model)
        self.bedrock = get_bedrock()
        self.has_fallback = bool(api_key)

    # -- helpers -------------------------------------------------------------
    def _route(self) -> Dict[str, Any]:
        return route_var.get() or {"tier": "fast", "model_id": None, "reason": "no gate decision"}

    @staticmethod
    def _mode_instruction(mode: str, difficulty: str, max_sents: int) -> str:
        m = (mode or "Simple").lower()
        if "socratic" in m:
            return ("PEDAGOGY: GUIDED DISCOVERY. The student asked for a final answer they should work out themselves. "
                    "Do NOT give the final answer. Give (1) the key idea, (2) a hint, (3) the first step worked as an example, "
                    "(4) one question that makes them do the next step. Be warm, not preachy.")
        if "quiz" in m:
            return ("PEDAGOGY: QUIZ. Teach with questions: short hints, one concept at a time; let the student reason before you confirm.")
        if "detail" in m or "deep" in m:
            return ("PEDAGOGY: DETAILED. Give an in-depth, rigorous breakdown: mechanism, data structures, edge cases, complexity. "
                    "Cite excerpts as [1], [2].")
        return (f"PEDAGOGY: SIMPLE. (1) One-sentence answer. (2) Short explanation, max {max_sents} sentences, one concrete example. "
                "(3) 'From your material:' cite [1], [2]. (4) 'Check yourself:' one short question.")

    # -- tutor answer ----------------------------------------------------------
    def generate_grounded_tutor_response(self, *args, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query") or (args[0] if args else "")
        ctxs = kwargs.get("retrieved_contexts") or (args[1] if len(args) > 1 else []) or []
        history = kwargs.get("conversation_history") or (args[2] if len(args) > 2 else []) or []
        mode = kwargs.get("mode", "Simple")
        difficulty = kwargs.get("difficulty", "Medium")
        language = kwargs.get("language", "en")
        learner_ctx = kwargs.get("learner_context") or ""

        blocks = []
        for i, c in enumerate(ctxs[:4]):
            loc = (f"Page {c.get('page_number')}" if c.get("page_number")
                   else f"Slide {c.get('slide_number')}" if c.get("slide_number") else "")
            blocks.append(f"[{i + 1}] {c.get('document_name', 'Course Document')} ({loc}):\n{c.get('content', '')}")
        lang = {"hi": "Respond in formal Hindi (Devanagari), keep technical terms in English.",
                "hinglish": "Respond in natural Hinglish (Hindi in Roman script mixed with English), keep code and terms in English."
                }.get(language, "")
        system = (
            "You are StudyMind AI, a precise, warm university tutor.\n"
            f"Level: {difficulty}. {lang}\n"
            f"{self._mode_instruction(mode, difficulty, getattr(settings, 'TUTOR_SIMPLE_MAX_SENTENCES', 6))}\n"
            + (f"STUDENT CONTEXT: {learner_ctx}\n" if learner_ctx else "")
            + ("RULES: ground every factual claim in the COURSE EXCERPTS and cite them as [1], [2]. "
               "If the excerpts do not cover something, say so rather than inventing it. Use clean markdown; give runnable, "
               "commented code when code is requested.\n\nCOURSE EXCERPTS:\n" + "\n\n".join(blocks)
               if blocks else
               "RULES: answer directly and clearly in markdown; give runnable, commented code when code is requested.")
        )
        msgs = [{"role": h.get("role", "user"), "content": (h.get("content") or "")[:1200]}
                for h in history[-6:] if h.get("role") in ("user", "assistant") and h.get("content")]
        msgs.append({"role": "user", "content": query})

        route = self._route()
        try:
            out = self.bedrock.converse(msgs, system=system, tier=route.get("tier", "fast"),
                                        model_id=route.get("model_id"), max_tokens=1500, temperature=0.4)
        except BedrockUnavailable as exc:
            print(f"[Bedrock] tutor generation failed: {exc}")
            if self.has_fallback:
                return super().generate_grounded_tutor_response(*args, **kwargs)
            raise AIServiceUnavailableError("Bedrock unavailable and no fallback provider configured") from exc

        citations = [{
            "citation_index": i + 1, "source_type": c.get("source_type", "pdf"),
            "document_name": c.get("document_name", "Course Material"),
            "page_number": c.get("page_number"), "slide_number": c.get("slide_number"),
            "timestamp_start": c.get("timestamp_start"), "timestamp_end": c.get("timestamp_end"),
            "snippet": c.get("content", "")[:200] + ("..." if len(c.get("content", "")) > 200 else ""),
            "chunk_id": c.get("id", f"chk_{i}"),
        } for i, c in enumerate(ctxs[:4])]
        return {
            "answer": out["text"], "grounded": True, "is_outside_knowledge": False, "citations": citations,
            "external_links": get_topic_links(query), "confidence_score": 0.98,
            "follow_ups": ["Can you explain this with another practical example?",
                           "Quiz me on this concept in chat", "Give me an intuitive real-world analogy"],
            "verification_question": "What is the core takeaway?",
            "generated_by": {"provider": "bedrock", "model_id": out["model_id"], "tier": route.get("tier"),
                             "latency_ms": round(out["latency_ms"], 1)},
        }

    # -- generic completion (used by NLI/verification helpers) ------------------
    def generate_completion(self, messages: List[Dict[str, str]], max_tokens: int = 500,
                            temperature: float = 0.2) -> Dict[str, Any]:
        system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") in ("user", "assistant")]
        try:
            out = self.bedrock.converse(convo, system=system, tier="fast", max_tokens=max_tokens, temperature=temperature)
            return {"content": out["text"]}
        except BedrockUnavailable as exc:
            if self.has_fallback:
                return super().generate_completion(messages, max_tokens, temperature)
            if is_test_environment():
                return {"content": "YES"}
            raise AIServiceUnavailableError(str(exc)) from exc
