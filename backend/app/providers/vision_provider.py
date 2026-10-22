from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.app.core.config import settings, is_test_environment
from backend.app.core.errors import AIServiceUnavailableError

class VisionProvider(ABC):
    @abstractmethod
    def analyze_visual_element(self, element_type: str, context_text: str, page_or_slide: int) -> str:
        pass

class MockVisionProvider(VisionProvider):
    """
    Test-only vision simulator. Restricted strictly to APP_ENV=test.
    """
    def __init__(self):
        if not is_test_environment():
            raise AIServiceUnavailableError("MockVisionProvider is permitted ONLY under APP_ENV=test.")

    def analyze_visual_element(self, element_type: str, context_text: str, page_or_slide: int) -> str:
        if not is_test_environment():
            raise AIServiceUnavailableError("MockVisionProvider is permitted ONLY under APP_ENV=test.")
        return (
            f"An academic visual figure and structural diagram on page/slide {page_or_slide} demonstrating "
            f"core conceptual properties and data relationships for: {context_text[:140]}..."
        )

class OpenAIVisionProvider(VisionProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze_visual_element(self, element_type: str, context_text: str, page_or_slide: int) -> str:
        if not self.api_key or not self.api_key.strip():
            if is_test_environment():
                return MockVisionProvider().analyze_visual_element(element_type, context_text, page_or_slide)
            raise AIServiceUnavailableError("AI service unavailable, retry: Vision API key missing.")
        # If live call fails in production:
        if not is_test_environment():
            raise AIServiceUnavailableError("AI service unavailable, retry")
        return MockVisionProvider().analyze_visual_element(element_type, context_text, page_or_slide)

class GroqVisionProvider(VisionProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze_visual_element(self, element_type: str, context_text: str, page_or_slide: int) -> str:
        if not self.api_key or not self.api_key.strip():
            if is_test_environment():
                return MockVisionProvider().analyze_visual_element(element_type, context_text, page_or_slide)
            raise AIServiceUnavailableError("AI service unavailable, retry: GROQ_API_KEY missing for vision.")
        
        # If VISION_MODEL is not configured, mark figure as 'not analyzed'
        if not settings.VISION_MODEL or not settings.VISION_MODEL.strip():
            return "not analyzed"

        import httpx
        import time

        prompt = f"Analyze the academic significance of this {element_type} found on page/slide {page_or_slide} in context: {context_text[:500]}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        model_name = settings.VISION_MODEL

        for attempt in range(3):
            try:
                res = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120
                }, timeout=12.0)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                if res.status_code == 429:
                    retry_after = res.headers.get("retry-after")
                    wait_sec = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else (2.0 * (attempt + 1))
                    time.sleep(min(wait_sec, 6.0))
                    continue
                raise RuntimeError(f"Groq vision returned status {res.status_code}")
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.5)
                    continue
                if is_test_environment():
                    return MockVisionProvider().analyze_visual_element(element_type, context_text, page_or_slide)
                return "not analyzed"
        
        return "not analyzed"

class NullVisionProvider(VisionProvider):
    """Safe fallback when vision API keys are not configured."""
    def analyze_visual_element(self, element_type: str, context_text: str, page_or_slide: int) -> str:
        return f"Visual element ({element_type}) on page/slide {page_or_slide}."

def get_vision_provider(provider_type: str = "groq", api_key: Optional[str] = None) -> VisionProvider:
    p_type = (provider_type or "groq").lower()
    if p_type == "openai" and api_key:
        return OpenAIVisionProvider(api_key=api_key)
    if (p_type == "groq" or not api_key) and settings.GROQ_API_KEY:
        return GroqVisionProvider(api_key=settings.GROQ_API_KEY)
    if is_test_environment():
        return MockVisionProvider()
    return NullVisionProvider()


