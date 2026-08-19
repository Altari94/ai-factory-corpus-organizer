from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "ai-factory-corpus-organizer"
    app_env: str = "development"
    log_level: str = "INFO"
    openai_api_key: str | None = None
    openai_llm_model: str = "gpt-5.2"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: float = 60.0
    openai_max_retries: int = 2
    openai_retry_base_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        app_name=os.getenv("APP_NAME", "ai-factory-corpus-organizer"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_llm_model=os.getenv("OPENAI_LLM_MODEL", "gpt-5.2"),
        openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        openai_timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
        openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        openai_retry_base_seconds=float(os.getenv("OPENAI_RETRY_BASE_SECONDS", "1")),
    )
