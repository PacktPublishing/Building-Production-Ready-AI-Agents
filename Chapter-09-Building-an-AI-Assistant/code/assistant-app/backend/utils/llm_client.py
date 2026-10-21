"""LLM client — thin wrapper around the Ollama Python SDK."""

import json
import logging
from typing import Any

import ollama

from backend.utils.config import Settings

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Raised when the LLM client encounters an error."""


class LLMClient:
    """Handles all communication with the Ollama LLM."""

    def __init__(self, settings: Settings) -> None:
        self._client = ollama.Client(host=settings.ollama_host)
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout

    @property
    def model_name(self) -> str:
        return self._model

    async def check_connection(self) -> bool:
        """Check if Ollama is reachable and the model is available."""
        try:
            models = self._client.list()
            available = [m.model for m in models.models]
            return any(self._model in name for name in available)
        except Exception as exc:
            logger.error("Ollama connection check failed: %s", exc)
            return False

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Send a prompt to the LLM and parse the JSON response.

        Args:
            system_prompt: The system-level instruction.
            user_prompt: The user message / ticket content.

        Returns:
            Parsed JSON dictionary from the LLM response.

        Raises:
            LLMClientError: If the LLM call or JSON parsing fails.
        """
        try:
            response = self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={"temperature": 0.1, "num_predict": 300, "num_ctx": 1024},
            )

            content = response.message.content.strip()
            logger.debug("LLM raw response: %s", content)

            return json.loads(content)

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s", exc)
            raise LLMClientError(f"Invalid JSON from LLM: {exc}") from exc
        except ollama.ResponseError as exc:
            logger.error("Ollama API error: %s", exc)
            raise LLMClientError(f"Ollama API error: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected LLM error: %s", exc)
            raise LLMClientError(f"LLM service error: {exc}") from exc
