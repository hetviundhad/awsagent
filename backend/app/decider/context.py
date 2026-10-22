"""Request-scoped hand-off between the gate, the RAG engine and the Bedrock provider (no signature changes needed)."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, Optional

# {"tier": "fast"|"deep", "model_id": str|None, "reason": str}
route_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("decider_route", default=None)
# mutable dict the engine fills with per-chunk relevance scores for the current request
context_scores_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("decider_context_scores", default=None)
