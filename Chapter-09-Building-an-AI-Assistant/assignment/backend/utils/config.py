from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral:latest"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_prefix="ASSISTANT_", env_file=".env")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
