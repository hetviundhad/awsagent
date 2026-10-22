import os
import re
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List, Set, Optional
import numpy as np
from backend.app.core.config import settings, is_test_environment
from backend.app.core.errors import AIServiceUnavailableError

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    def generate_embedding(self, text: str) -> List[float]:
        return self.embed_text(text)

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

class TransformerEmbeddingProvider(EmbeddingProvider):
    """
    Production-grade local semantic embedding provider using HuggingFace Transformers
    with mean-pooling and L2 normalization (384 dimensions, sentence-transformers/all-MiniLM-L6-v2).
    Generates real semantic embeddings across any academic domain (Biology, Physics, History, etc.).
    """
    _instance = None
    _tokenizer = None
    _model = None

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        if TransformerEmbeddingProvider._model is None:
            try:
                import torch
                from transformers import AutoTokenizer, AutoModel
                TransformerEmbeddingProvider._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                TransformerEmbeddingProvider._model = AutoModel.from_pretrained(self.model_name)
                TransformerEmbeddingProvider._model.eval()
            except Exception as e:
                if not is_test_environment():
                    raise RuntimeError(f"AI service unavailable, retry: Failed to initialize transformer embeddings ({e})")

    def embed_text(self, text: str) -> List[float]:
        results = self.embed_batch([text])
        return results[0] if results else [0.0] * 384

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if TransformerEmbeddingProvider._model is None:
            self._load_model()

        if TransformerEmbeddingProvider._model is None:
            if is_test_environment():
                return MockEmbeddingProvider().embed_batch(texts)
            raise RuntimeError("AI service unavailable, retry")

        try:
            import torch
            clean_texts = [t.strip() if t and t.strip() else " " for t in texts]
            tokens = TransformerEmbeddingProvider._tokenizer(
                clean_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            with torch.no_grad():
                output = TransformerEmbeddingProvider._model(**tokens)
                token_embeddings = output[0] # First element of model_output contains token embeddings
                attention_mask = tokens['attention_mask'].unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * attention_mask, 1)
                sum_mask = torch.clamp(attention_mask.sum(1), min=1e-9)
                mean_pooled = sum_embeddings / sum_mask
                normalized = torch.nn.functional.normalize(mean_pooled, p=2, dim=1)
                return normalized.cpu().tolist()
        except Exception as e:
            if is_test_environment():
                return MockEmbeddingProvider().embed_batch(texts)
            raise RuntimeError(f"AI service unavailable, retry: {str(e)}")

STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "each", "few", "for", "from", "further", "had", "has", "have", "he", "her", "here", "him", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "me", "more", "most", "my", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "our", "out", "over", "own", "same", "she", "so",
    "some", "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your"
}

def _stem_word(w: str) -> str:
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 3:
        return w[:-2]
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("ed") and len(w) > 4:
        return w[:-2]
    return w

class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock Embedding Provider for isolated unit testing under pytest.
    Strictly forbidden in production/live user flows.
    """
    DIMENSIONS = 384

    def __init__(self):
        if not is_test_environment():
            raise RuntimeError("MockEmbeddingProvider is permitted ONLY under pytest/testing environment. In production, use real embeddings.")

    def _generate_vector(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.DIMENSIONS

        clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        raw_words = [w for w in clean.split() if w]
        if not raw_words:
            return [0.0] * self.DIMENSIONS

        vec = np.zeros(self.DIMENSIONS, dtype=np.float32)
        for word in raw_words:
            if word in STOP_WORDS:
                continue
            stem = _stem_word(word)
            h = int(hashlib.sha256(stem.encode('utf-8')).hexdigest(), 16)
            for shift in (0, 8, 16):
                idx = (h >> shift) % self.DIMENSIONS
                vec[idx] += 3.0
            padded = f"<{stem}>"
            for n in (3, 4, 5):
                for i in range(len(padded) - n + 1):
                    ngram = padded[i:i+n]
                    h_ng = int(hashlib.md5(ngram.encode('utf-8')).hexdigest(), 16)
                    idx_ng = h_ng % self.DIMENSIONS
                    vec[idx_ng] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec.tolist()

    def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def embed_text(self, text: str) -> List[float]:
        res = self.embed_batch([text])
        return res[0] if res else [0.0] * 384

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            if is_test_environment():
                return MockEmbeddingProvider().embed_batch(texts)
            raise RuntimeError("AI service unavailable, retry: OPENAI_API_KEY missing")
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"model": "text-embedding-3-small", "input": texts}
            res = httpx.post("https://api.openai.com/v1/embeddings", json=payload, headers=headers, timeout=15.0)
            if res.status_code == 200:
                data = res.json()["data"]
                return [d["embedding"] for d in data]
            raise RuntimeError(f"OpenAI embedding API returned status {res.status_code}")
        except Exception as e:
            if is_test_environment():
                return MockEmbeddingProvider().embed_batch(texts)
            raise RuntimeError(f"AI service unavailable, retry: {str(e)}")

def get_embedding_provider(provider_type: str = "transformers", api_key: Optional[str] = None) -> EmbeddingProvider:
    p_type = (provider_type or "transformers").lower()
    if p_type == "openai" and api_key:
        return OpenAIEmbeddingProvider(api_key=api_key)
    if p_type == "mock":
        if is_test_environment():
            return MockEmbeddingProvider()
        return TransformerEmbeddingProvider()
    return TransformerEmbeddingProvider()
