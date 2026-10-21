from __future__ import annotations

import logging

import ollama

from backend.utils.config import Settings

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._client = ollama.Client(host=settings.ollama_host)
        self._model = settings.ollama_model

    @property
    def model_name(self) -> str:
        return self._model

    async def check_connection(self) -> bool:
        try:
            models = self._client.list()
            return any(self._model in model.model for model in models.models)
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return False

    def answer(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.2, "num_predict": 220, "num_ctx": 2048},
            )
            return response.message.content.strip()
        except Exception as exc:
            raise LLMClientError(str(exc)) from exc
