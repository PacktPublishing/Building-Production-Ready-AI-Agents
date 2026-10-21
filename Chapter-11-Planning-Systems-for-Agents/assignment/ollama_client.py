from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Any

import httpx
from pydantic import ValidationError

from app_models import BagelExtraction, BagelState, PizzaExtraction, PizzaState


class OllamaClient:
    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.extract_model = os.getenv("OLLAMA_EXTRACT_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
        self.rewrite_model = os.getenv("OLLAMA_REWRITE_MODEL", self.extract_model)
        self.timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "20"))
        self.extract_retries = int(os.getenv("OLLAMA_EXTRACT_RETRIES", "1"))

    def _classify_ollama_error(self, error: Exception) -> dict[str, Any]:
        if isinstance(error, httpx.TimeoutException):
            return {"type": "timeout", "message": str(error)}
        if isinstance(error, httpx.ConnectError):
            return {"type": "connect", "message": str(error)}
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code if error.response is not None else None
            return {
                "type": "http",
                "message": str(error),
                "status_code": status_code,
            }
        return {"type": "unknown", "message": str(error)}

    def _chat_with_meta(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Any = None,
        model: str | None = None,
        retries: int = 0,
    ) -> tuple[str | None, dict[str, Any], int]:
        chosen_model = model or self.extract_model
        max_attempts = max(1, retries + 1)
        last_error: dict[str, Any] | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    payload: dict[str, Any] = {
                        "model": chosen_model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    }
                    if response_format is not None:
                        payload["format"] = response_format

                    response = client.post(
                        f"{self.host}/api/chat",
                        json=payload,
                    )
                    response.raise_for_status()
                    content = response.json().get("message", {}).get("content", "").strip()
                    if content:
                        return content, {"type": None, "message": None}, attempt

                    last_error = {
                        "type": "empty_content",
                        "message": "Ollama returned an empty message content",
                    }
            except Exception as exc:
                last_error = self._classify_ollama_error(exc)

        return None, (last_error or {"type": "unknown", "message": "Extractor failed with no details"}), max_attempts

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Any = None,
        model: str | None = None,
    ) -> str | None:
        content, _, _ = self._chat_with_meta(
            system_prompt,
            user_prompt,
            response_format=response_format,
            model=model,
            retries=0,
        )
        return content

    def rewrite_reply(self, raw_reply: str) -> str:
        if "\n" in raw_reply:
            return raw_reply

        system = (
            "You are a concise pizza ordering assistant. Keep the message under 2 short paragraphs. "
            "Keep all facts and constraints from the draft. Do not add new facts."
        )
        rewritten = self._chat(system, raw_reply, model=self.rewrite_model)
        return rewritten if rewritten else raw_reply

    def extract_order_update(self, message: str, state: PizzaState) -> tuple[dict[str, Any], dict[str, Any]]:
        system = (
            "Extract pizza ordering updates from the user message into JSON. "
            "Return JSON only, with no markdown fences or prose. "
            "Allowed keys: size, crust, add_toppings, replace_toppings, remove_toppings, "
            "address, payment_method, confirmed, approved_eta_override, review_rejected, allergies. "
            "Use null for unknown scalar values and [] for unknown arrays. "
            "Only include toppings explicitly mentioned by the user. "
            "If the user changes toppings completely, use replace_toppings. "
            "If the user wants to remove toppings, use remove_toppings. "
            "If the user rejects the review or wants to revise before ordering, set review_rejected to true. "
            "Do not infer missing address details."
        )
        user_prompt = json.dumps(
            {
                "message": message,
                "current_state": asdict(state),
                "allowed_sizes": ["small", "medium", "large"],
                "allowed_crusts": ["thin", "thick", "gluten-free", "stuffed"],
                "allowed_payment_methods": ["card", "cash", "swish", "paypal"],
                "allowed_toppings": [
                    "pepperoni",
                    "mushrooms",
                    "onions",
                    "olives",
                    "ham",
                    "pineapple",
                    "cheese",
                    "jalapeno",
                    "bacon",
                    "tomato",
                    "anchovy",
                    "paprika",
                ],
                "allowed_allergies": ["nuts", "peanuts", "gluten", "dairy", "lactose"],
            }
        )
        content, extractor_error, attempts = self._chat_with_meta(
            system,
            user_prompt,
            response_format=PizzaExtraction.model_json_schema(),
            model=self.extract_model,
            retries=self.extract_retries,
        )
        if not content:
            return {}, {
                "mode": "llm",
                "success": False,
                "error": "No response from extractor",
                "raw_response": None,
                "extractor_error": extractor_error,
                "extractor_attempts": attempts,
                "extractor_model": self.extract_model,
            }

        try:
            extracted = PizzaExtraction.model_validate_json(content)
        except ValidationError:
            try:
                parsed = self._parse_json_object(content)
                extracted = PizzaExtraction.model_validate(parsed)
            except (ValueError, ValidationError) as exc:
                return {}, {
                    "mode": "llm",
                    "success": False,
                    "error": str(exc),
                    "raw_response": content,
                    "extractor_error": {"type": "parse", "message": str(exc)},
                    "extractor_attempts": attempts,
                    "extractor_model": self.extract_model,
                }

        parsed = extracted.model_dump()
        normalized = self._normalize_extracted_update(parsed)
        success = bool(normalized)
        return normalized, {
            "mode": "llm",
            "success": success,
            "error": None if success else "Extractor returned JSON but no usable fields were recognized",
            "raw_response": content,
            "parsed_json": parsed,
            "normalized_updates": normalized,
            "extractor_error": None,
            "extractor_attempts": attempts,
            "extractor_model": self.extract_model,
        }

    def extract_bagel_update(self, message: str, state: BagelState) -> tuple[dict[str, Any], dict[str, Any]]:
        system = (
            "Extract bagel ordering updates from the user message into JSON. "
            "Return JSON only, with no markdown fences or prose. "
            "Allowed keys: bread_type, filling, add_extras, replace_extras, remove_extras, "
            "address, payment_method, confirmed, approved_eta_override, review_rejected, allergies. "
            "Use null for unknown scalar values and [] for unknown arrays. "
            "Only include values explicitly mentioned by the user."
        )
        user_prompt = json.dumps(
            {
                "message": message,
                "current_state": asdict(state),
                "allowed_bread_types": ["sesame", "plain", "everything", "whole wheat", "poppy seed"],
                "allowed_fillings": ["cream cheese", "roast beef", "turkey", "salmon", "avocado", "ham"],
                "allowed_extras": ["onion", "tomato", "lettuce", "cucumber", "capers", "jalapeno", "cheese"],
                "allowed_payment_methods": ["card", "cash", "swish", "paypal"],
                "allowed_allergies": ["nuts", "peanuts", "gluten", "dairy", "lactose"],
            }
        )
        content, extractor_error, attempts = self._chat_with_meta(
            system,
            user_prompt,
            response_format=BagelExtraction.model_json_schema(),
            model=self.extract_model,
            retries=self.extract_retries,
        )
        if not content:
            return {}, {
                "mode": "llm",
                "success": False,
                "error": "No response from extractor",
                "raw_response": None,
                "extractor_error": extractor_error,
                "extractor_attempts": attempts,
                "extractor_model": self.extract_model,
            }

        try:
            extracted = BagelExtraction.model_validate_json(content)
        except ValidationError:
            try:
                parsed = self._parse_json_object(content)
                extracted = BagelExtraction.model_validate(parsed)
            except (ValueError, ValidationError) as exc:
                return {}, {
                    "mode": "llm",
                    "success": False,
                    "error": str(exc),
                    "raw_response": content,
                    "extractor_error": {"type": "parse", "message": str(exc)},
                    "extractor_attempts": attempts,
                    "extractor_model": self.extract_model,
                }

        parsed = extracted.model_dump()
        normalized = self._normalize_bagel_update(parsed)
        success = bool(normalized)
        return normalized, {
            "mode": "llm",
            "success": success,
            "error": None if success else "Extractor returned JSON but no usable fields were recognized",
            "raw_response": content,
            "parsed_json": parsed,
            "normalized_updates": normalized,
            "extractor_error": None,
            "extractor_attempts": attempts,
            "extractor_model": self.extract_model,
        }

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found")

        parsed = json.loads(stripped[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        return parsed

    def _normalize_extracted_update(self, parsed: dict[str, Any]) -> dict[str, Any]:
        topping_aliases = {
            "mushroom": "mushrooms",
            "mushrooms": "mushrooms",
            "onion": "onions",
            "onions": "onions",
            "jalapeño": "jalapeno",
        }

        allowed_scalars = {
            "size": {"small", "medium", "large"},
            "crust": {"thin", "thick", "gluten-free", "stuffed"},
            "payment_method": {"card", "cash", "swish", "paypal"},
        }
        allowed_lists = {
            "add_toppings": {
                "pepperoni",
                "mushrooms",
                "onions",
                "olives",
                "ham",
                "pineapple",
                "cheese",
                "jalapeno",
                "bacon",
                "tomato",
                "anchovy",
                "paprika",
            },
            "replace_toppings": {
                "pepperoni",
                "mushrooms",
                "onions",
                "olives",
                "ham",
                "pineapple",
                "cheese",
                "jalapeno",
                "bacon",
                "tomato",
                "anchovy",
                "paprika",
            },
            "remove_toppings": {
                "pepperoni",
                "mushrooms",
                "onions",
                "olives",
                "ham",
                "pineapple",
                "cheese",
                "jalapeno",
                "bacon",
                "tomato",
                "anchovy",
                "paprika",
            },
            "allergies": {"nuts", "peanuts", "gluten", "dairy", "lactose"},
        }
        normalized: dict[str, Any] = {}

        for key, allowed in allowed_scalars.items():
            value = parsed.get(key)
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in allowed:
                    normalized[key] = lowered

        for key, allowed in allowed_lists.items():
            value = parsed.get(key)
            if isinstance(value, list):
                cleaned = sorted(
                    {
                        topping_aliases.get(str(item).strip().lower(), str(item).strip().lower())
                        for item in value
                        if isinstance(item, str)
                        and topping_aliases.get(str(item).strip().lower(), str(item).strip().lower()) in allowed
                    }
                )
                if cleaned:
                    normalized[key] = cleaned

        address = parsed.get("address")
        if isinstance(address, str) and address.strip():
            normalized["address"] = address.strip().title()

        for key in ["confirmed", "approved_eta_override", "review_rejected"]:
            value = parsed.get(key)
            if isinstance(value, bool):
                normalized[key] = value

        return normalized

    def _normalize_bagel_update(self, parsed: dict[str, Any]) -> dict[str, Any]:
        allowed_scalars = {
            "bread_type": {"sesame", "plain", "everything", "whole wheat", "poppy seed"},
            "filling": {"cream cheese", "roast beef", "turkey", "salmon", "avocado", "ham"},
            "payment_method": {"card", "cash", "swish", "paypal"},
        }
        allowed_lists = {
            "add_extras": {"onion", "tomato", "lettuce", "cucumber", "capers", "jalapeno", "cheese"},
            "replace_extras": {"onion", "tomato", "lettuce", "cucumber", "capers", "jalapeno", "cheese"},
            "remove_extras": {"onion", "tomato", "lettuce", "cucumber", "capers", "jalapeno", "cheese"},
            "allergies": {"nuts", "peanuts", "gluten", "dairy", "lactose"},
        }
        normalized: dict[str, Any] = {}

        for key, allowed in allowed_scalars.items():
            value = parsed.get(key)
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in allowed:
                    normalized[key] = lowered

        for key, allowed in allowed_lists.items():
            value = parsed.get(key)
            if isinstance(value, list):
                cleaned = sorted(
                    {
                        str(item).strip().lower()
                        for item in value
                        if isinstance(item, str) and str(item).strip().lower() in allowed
                    }
                )
                if cleaned:
                    normalized[key] = cleaned

        address = parsed.get("address")
        if isinstance(address, str) and address.strip():
            normalized["address"] = address.strip().title()

        for key in ["confirmed", "approved_eta_override", "review_rejected"]:
            value = parsed.get(key)
            if isinstance(value, bool):
                normalized[key] = value

        return normalized
