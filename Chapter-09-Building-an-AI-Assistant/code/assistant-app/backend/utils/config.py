"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    ollama_timeout: float = 120.0
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    model_config = {"env_prefix": "TRIAGE_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
