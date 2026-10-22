import os
from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    APP_ENV: str = "development"  # test, development, production
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    # Supabase credentials
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "course-materials"
    
    # AI Providers (groq, transformers, openai, gemini, anthropic, ollama, mock)
    # Default is real Groq LLM + Transformers Embeddings; mock is restricted to pytest with APP_ENV=test.
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_MODEL_EXTRACT: str = "openai/gpt-oss-120b"
    LLM_MODEL_FAST: Optional[str] = "openai/gpt-oss-20b"
    LLM_MODEL_CRITIC: Optional[str] = "qwen/qwen3.8-27b"
    VISION_MODEL: Optional[str] = None
    FIGURE_MIN_WIDTH: int = 80
    FIGURE_MIN_HEIGHT: int = 80
    FIGURE_MIN_BYTES: int = 1500
    EMBEDDING_PROVIDER: str = "transformers"
    VISION_PROVIDER: str = "groq"
    STT_PROVIDER: str = "groq"
    
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_URL: str = "http://localhost:11434"
    CUSTOM_API_BASE: Optional[str] = None
    CUSTOM_API_KEY: Optional[str] = None
    
    # Amazon Bedrock + Strands Decider 2B
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_FAST: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    BEDROCK_MODEL_DEEP: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    STRANDS_DECIDER_URL: str = "http://127.0.0.1:8099"
    DECIDER_ALLOW_FALLBACK: bool = True
    DECIDER_CONTEXT_SCORING: bool = True
    EMBEDDING_DIMENSION: int = 384

    # RAG Settings & Calibration
    RETRIEVAL_CONFIDENCE_THRESHOLD: float = 0.35
    RETRIEVAL_REFUSAL_THRESHOLD: float = 0.30
    MAX_RETRIEVED_CHUNKS: int = 5
    HYBRID_SEARCH_MODE: str = "rrf" # rrf (Reciprocal Rank Fusion), linear, dense_only, bm25_only
    RERANK_ENABLED: bool = False
    RRF_K: int = 60
    SELF_RAG_MAX_FAILED_CLAIMS_SHARE: float = 0.50
    SELF_RAG_MIN_OVERLAP_TOKENS: int = 2
    ADAPTIVE_DEPTH_BEGINNER_THRESHOLD: float = 0.40
    ADAPTIVE_DEPTH_ADVANCED_THRESHOLD: float = 0.70
    CALIBRATION_MIN_THRESHOLD: float = 0.10
    CALIBRATION_MAX_THRESHOLD: float = 0.70
    CALIBRATION_THRESHOLD_STEPS: int = 61
    NUMERICAL_TOLERANCE_DEFAULT: float = 0.01
    QUESTION_SUPPORT_QUOTE_MIN_SIM: float = 0.75
    
    # RAG Engine Float Constants
    FLOAT_ZERO: float = 0.0
    FLOAT_ONE: float = 1.0
    RAG_SEMANTIC_WEIGHT: float = 0.70
    RAG_KEYWORD_WEIGHT: float = 0.30
    RAG_SCORE_SCALE: float = 30.0
    RAG_SCORE_OFFSET: float = 1.5
    RAG_MAX_CONFIDENCE: float = 0.99
    RAG_SIMILARITY_MIN_OVERLAP: float = 0.40
    RAG_EXACT_MATCH_BONUS: float = 0.80
    RAG_NLI_TEMPERATURE: float = 0.0
    RAG_NLI_MAX_TOKENS: int = 400
    RAG_LLM_VERSION_QWEN: float = 3.3
    RAG_LLM_VERSION_LLAMA: float = 6.0
    RAG_SYLLABUS_REFUSAL_THRESHOLD: float = 0.45
    
    # Ingestion, Chunking & Performance Calibration
    CHUNK_MIN_WORDS: int = 35
    CHUNK_MAX_WORDS: int = 300
    CHUNK_MIN_CHARS: int = 120
    CHUNK_OVERLAP_PCT: float = 0.15
    CHUNK_SIMILARITY_DEDUP_THRESHOLD: float = 0.92
    MEDIA_WINDOW_MIN_SEC: int = 60
    MEDIA_WINDOW_MAX_SEC: int = 90
    CONCEPT_SIMILARITY_MERGE_THRESHOLD: float = 0.88
    CONCEPT_MERGE_HIGH_SIM: float = 0.90
    CONCEPT_MERGE_LOW_SIM: float = 0.78
    CHUNK_TAG_THRESHOLD: float = 0.55
    CHUNK_TAG_TOP_K: int = 4
    INGEST_MAX_WORKERS: int = 4
    EMBED_BATCH_SIZE: int = 64
    DB_DEBOUNCE_SECONDS: float = 2.0
    LLM_MAX_CONCURRENCY: int = 2
    
    # Bayesian Knowledge Tracing (BKT) Defaults & Calibrated Constants
    BKT_P_INIT: float = 0.20
    BKT_P_TRANSIT: float = 0.15
    BKT_P_SLIP: float = 0.10
    BKT_P_GUESS: float = 0.20
    BKT_UNLOCK_THRESHOLD: float = 0.60
    REVIEW_DAYS_LOW: int = 1
    REVIEW_DAYS_MED: int = 3
    REVIEW_DAYS_HIGH: int = 7
    
    BKT_MASTERY_LOW: float = 0.45
    BKT_MASTERY_HIGH: float = 0.75
    BKT_DEFAULT_CONFIDENCE: float = 0.50
    BKT_PERCENT_SCALE: float = 100.0
    BKT_ATTEMPT_MIN_CORRECT_WEIGHT: float = 0.20
    BKT_MAX_PROB: float = 1.0
    BKT_PROB_FLOOR: float = 0.01
    BKT_PROB_CEIL: float = 0.99
    BKT_REINFORCE_DECAY: float = 0.40
    BKT_WEIGHT_SLIP_TOLERANCE: float = 0.08
    BKT_WEIGHT_GUESS_TOLERANCE: float = 0.95
    BKT_DEFAULT_ZERO: float = 0.0
    BKT_DIAGNOSTIC_PRIOR_DEFAULT: float = 0.70
    BKT_DIAGNOSTIC_PRIOR_WEAK: float = 0.80
    BKT_DIAGNOSTIC_BASE_SCALE: float = 33.3
    BKT_MASTERY_THRESHOLD: float = 0.70
    BKT_INTERVENT_THRESHOLD: float = 0.65
    BKT_INTERVENT_WINDOW_MIN: float = 0.20
    BKT_INTERVENT_WINDOW_MAX: float = 0.40
    BKT_PARAM_EPSILON: float = 0.15
    BKT_PARAM_HIGH_BOUND: float = 0.85
    BKT_PRIOR_WEIGHT_CONFIDENCE: float = 0.72
    BKT_UPDATE_WEIGHT_CORRECT: float = 0.60
    BKT_UPDATE_WEIGHT_INCORRECT: float = 0.40
    BKT_FLASHCARD_BASE_HALF_LIFE: float = 86400.0
    BKT_FORGETTING_RATE: float = 0.05
    BKT_RETENTION_THRESHOLD: float = 0.60
    BKT_TUTOR_WEIGHT: float = 0.15
    BKT_QUIZ_WEIGHT: float = 1.0
    BKT_FLASHCARD_WEIGHT: float = 0.35
    BKT_PREREQ_LOCK_MIN_ATTEMPTS: int = 3
    
    # Confidence-Calibrated BKT Settings (Part 5)
    BKT_CONFIDENCE_GUESS_DISCOUNT: float = 0.40
    BKT_CONFIDENCE_WRONG_PENALTY: float = 1.45
    BKT_SUBJ_PROB_SURE: float = 0.90
    BKT_SUBJ_PROB_NOT_SURE: float = 0.60
    BKT_SUBJ_PROB_GUESS: float = 0.30

    # Assessment & Deduplication Defaults

    DEDUP_QUESTION_THRESHOLD: float = 0.85
    QUESTION_MAX_RETRIES: int = 3
    DIFFICULTY_LEVELS: List[str] = ["Beginner", "Intermediate", "Advanced", "Adaptive"]
    FREE_QUIZ_LIMIT: Optional[int] = None
    QUESTION_MIN_COUNT: int = 1
    QUESTION_MAX_COUNT: int = 25
    QUESTION_PRACTICAL_RATIO_DEFAULT: float = 0.70
    BKT_ADAPTIVE_BEGINNER_CUTOFF: float = 0.40
    BKT_ADAPTIVE_ADVANCED_CUTOFF: float = 0.75
    BKT_TARGET_SUCCESS_RATE: float = 0.70
    TUTOR_SIMPLE_MAX_SENTENCES: int = 6
    TUTOR_STYLES: List[str] = ["Simple", "Detailed", "Quiz me"]

    # Global Numerical Constants & Weights for BKT and RAG
    FLOAT_ZERO: float = 0.0
    FLOAT_ONE: float = 1.0
    FLOAT_HALF: float = 0.50
    FLOAT_EPSILON: float = 1e-6
    FLOAT_HUNDRED: float = 100.0
    FLOAT_FIFTY: float = 50.0
    BKT_HALF_LIFE_DEFAULT: float = 30.0
    BKT_DAY_SECONDS: float = 86400.0
    BKT_INTAKE_ADVANCED_PRIOR: float = 0.65
    BKT_INTAKE_INTERMEDIATE_PRIOR: float = 0.40
    BKT_INTAKE_BEGINNER_PRIOR: float = 0.20
    BKT_INTAKE_DIAGNOSTIC_MIN: float = 0.15
    BKT_INTAKE_DIAGNOSTIC_MAX: float = 0.85
    BKT_INTAKE_FAMILIAR_PRIOR: float = 0.72
    BKT_INTAKE_FAMILIAR_CONFIDENCE: float = 0.60
    BKT_INTAKE_UNFAMILIAR_CONFIDENCE: float = 0.40
    BKT_CONFIDENCE_ATTEMPT_WEIGHT: float = 0.08
    BKT_CONFIDENCE_CAP: float = 0.95
    BKT_DEFAULT_RECORD_CONFIDENCE: float = 0.80
    BKT_RECOM_URGENCY_OFFSET: float = 100.0
    BKT_RECOM_PRIORITY_OFFSET: float = 50.0
    BKT_RECOM_PRIORITY_SCALE: float = 50.0
    BKT_PREREQ_READINESS_BOOST: float = 0.05
    BKT_TOPIC_MASTERY_HIGH: float = 0.70
    BKT_DOC_COVERAGE_SCALE: float = 33.3

    # RAG Hybrid & Scoring Constants
    RAG_SEMANTIC_WEIGHT: float = 0.70
    RAG_BM25_WEIGHT: float = 0.30
    RAG_RRF_MULTIPLIER: float = 30.0
    RAG_SIGNAL_MULTIPLIER: float = 1.5
    RAG_BM_SIGNAL_BOOST: float = 0.80
    RAG_SUPPORT_HEURISTIC_THRESHOLD: float = 0.40
    RAG_PERFECT_CONFIDENCE: float = 1.0
    RAG_HIGH_CONFIDENCE: float = 0.99
    RAG_HTTP_TIMEOUT_SHORT: float = 6.0
    RAG_TEMPERATURE_DETERMINISTIC: float = 0.0
    
    # Data directory
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "storage")
    STUDYMIND_DB_PATH: Optional[str] = None

    @property
    def DB_PATH(self) -> str:
        env_val = os.getenv("STUDYMIND_DB_PATH")
        if env_val:
            return env_val
        if self.STUDYMIND_DB_PATH:
            return self.STUDYMIND_DB_PATH
        return os.path.join(self.STORAGE_DIR, "studymind_db.json")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

def _export_dotenv_to_environ() -> None:
    """pydantic loads .env into `settings` but NOT into os.environ. boto3 and the decider package read os.environ,
    so mirror the .env file there (real environment variables always win)."""
    try:
        from dotenv import dotenv_values
        for _k, _v in dotenv_values(".env").items():
            if _v not in (None, "") and _k not in os.environ:
                os.environ[_k] = str(_v)
    except Exception:
        pass
    os.environ.setdefault("STORAGE_DIR", settings.STORAGE_DIR)

_export_dotenv_to_environ()

def is_test_environment() -> bool:
    """Explicitly check APP_ENV set by conftest. No sys.modules inspection."""
    return settings.APP_ENV == "test"
