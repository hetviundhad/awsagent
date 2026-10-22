class AIServiceUnavailableError(Exception):
    """Raised when an AI provider (LLM, Embeddings, Vision, STT) fails in production without fallback."""
    def __init__(self, message: str = "AI service unavailable, retry"):
        super().__init__(message)
        self.message = message
