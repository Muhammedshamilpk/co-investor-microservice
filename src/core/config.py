"""
Application configuration via environment variables.
Uses pydantic-settings for type-safe, validated config loading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "Valura AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development | staging | production

    # LLM
    LLM_PROVIDER: str = "openai"        # openai | anthropic | gemini
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SECONDS: int = 30

    # Safety
    SAFETY_BLOCK_THRESHOLD: float = 0.85   # confidence above which request is blocked
    SAFETY_ENABLE_PROFANITY_CHECK: bool = True

    # Intent Classifier
    INTENT_CONFIDENCE_THRESHOLD: float = 0.6  # below → fallback agent

    # Streaming
    SSE_HEARTBEAT_INTERVAL: float = 15.0   # seconds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
