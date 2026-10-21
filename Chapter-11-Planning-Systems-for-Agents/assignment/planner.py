from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from typing import Any

from app_models import BagelState, PizzaState, PlanStep
from ollama_client import OllamaClient


class Planner(ABC):
    REQUIRED_FIELD_STEPS: list[tuple[str, str]] = []

    def __init__(self, llm: OllamaClient | None = None, enable_fallback: bool | None = None) -> None:
        self.llm = llm
        if enable_fallback is None:
            enable_fallback = os.getenv("ENABLE_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.enable_fallback = enable_fallback

    def extract_user_updates(self, message: str, state: PizzaState | BagelState | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.llm is None or state is None:
            return {}, {"mode": "llm", "success": False, "error": "LLM extractor unavailable"}

        llm_updates, llm_meta = self._extract_with_llm(message, state)
        if llm_updates:
            return llm_updates, llm_meta

        extractor_error_text = str(llm_meta.get("error") or "").lower()
        extractor_unavailable = llm_meta.get("raw_response") is None or "no response" in extractor_error_text
        allow_rescue_fallback = self.enable_fallback or extractor_unavailable
        if not allow_rescue_fallback:
            return {}, llm_meta

        fallback_updates = self._fallback_extract_from_text(message)
        if fallback_updates:
            return fallback_updates, {
                "mode": "fallback",
                "success": True,
                "reason": "Used deterministic fallback because LLM extractor returned no usable fields",
                "llm_extraction": llm_meta,
                "normalized_updates": fallback_updates,
            }

        return {}, llm_meta

    @abstractmethod
    def _extract_with_llm(self, message: str, state: PizzaState | BagelState) -> tuple[dict[str, Any], dict[str, Any]]:
        ...

    @abstractmethod
    def _fallback_extract_from_text(self, message: str) -> dict[str, Any]:
        ...

    def build_plan(self, state: PizzaState | BagelState) -> list[PlanStep]:
        plan: list[PlanStep] = []

        for field_name, step_name in self.REQUIRED_FIELD_STEPS:
            value = getattr(state, field_name)
            is_missing = value is None or (isinstance(value, list) and len(value) == 0)
            if is_missing:
                plan.append(PlanStep(step_name))

        if plan:
            return plan

        plan.append(PlanStep("check_constraints"))

        if state.review_rejected:
            plan.append(PlanStep("ask_changes"))
            return plan

        if not state.confirmed:
            plan.append(PlanStep("ask_confirm"))
            return plan

        plan.append(PlanStep("charge_payment"))
        plan.append(PlanStep("place_order"))
        return plan

    def missing_requirements(self, state: PizzaState | BagelState) -> list[str]:
        missing: list[str] = []

        for field_name, _ in self.REQUIRED_FIELD_STEPS:
            value = getattr(state, field_name)
            is_missing = value is None or (isinstance(value, list) and len(value) == 0)
            if is_missing:
                missing.append(field_name)

        if not state.confirmed:
            missing.append("confirmation")
        return missing

    def _looks_like_address(self, message: str) -> bool:
        raw = message.strip()
        if len(raw) < 6:
            return False

        has_number = bool(re.search(r"\d", raw))
        has_word = bool(re.search(r"[A-Za-z]", raw))
        looks_structured = "," in raw or bool(re.search(r"\b(st|street|ave|avenue|road|rd|ny)\b", raw.lower()))

        return has_number and has_word and looks_structured


class PizzaPlanner(Planner):
    SIZES = {"small", "medium", "large"}
    CRUSTS = {"thin", "thick", "gluten-free", "stuffed"}
    PAYMENT = {"card", "cash", "swish", "paypal"}
    TOPPING_VOCAB = [
        "pepperoni",
        "mushroom",
        "mushrooms",
        "onion",
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
    ]
    TOPPING_CANONICAL = {
        "mushroom": "mushrooms",
        "mushrooms": "mushrooms",
        "onion": "onions",
        "onions": "onions",
        "jalapeño": "jalapeno",
    }
    REQUIRED_FIELD_STEPS = [
        ("size", "ask_size"),
        ("crust", "ask_crust"),
        ("toppings", "ask_toppings"),
        ("address", "ask_address"),
        ("payment_method", "ask_payment"),
    ]

    def _extract_with_llm(self, message: str, state: PizzaState | BagelState) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(state, PizzaState):
            return {}, {"mode": "llm", "success": False, "error": "Invalid state for PizzaPlanner"}
        return self.llm.extract_order_update(message, state)

    def _fallback_extract_from_text(self, message: str) -> dict[str, Any]:
        m = message.lower()
        updates: dict[str, Any] = {}

        for size in self.SIZES:
            if re.search(rf"\b{re.escape(size)}\b", m):
                updates["size"] = size

        for crust in self.CRUSTS:
            if re.search(rf"\b{re.escape(crust)}\b", m):
                updates["crust"] = crust

        payments_map = {
            "credit card": "card",
            "debit card": "card",
            "card": "card",
            "cash": "cash",
            "swish": "swish",
            "paypal": "paypal",
        }
        for key, value in payments_map.items():
            if key in m:
                updates["payment_method"] = value

        if "confirm" in m or "place order" in m or "go ahead" in m:
            updates["confirmed"] = True

        if re.search(r"\b(reject|cancel order|dont place|don't place|not correct)\b", m):
            updates["review_rejected"] = True

        if "accept" in m and "eta" in m:
            updates["approved_eta_override"] = True
        if "override" in m and "eta" in m:
            updates["approved_eta_override"] = True

        allergy_terms = ["nuts", "peanuts", "gluten", "dairy", "lactose"]
        allergies = [term for term in allergy_terms if re.search(rf"\b{term}\b", m)]
        if allergies:
            updates["allergies"] = sorted(set(allergies))

        address_match = re.search(r"(?:deliver to|address is)\s+([a-z0-9][a-z0-9\s,\-]{5,})", m)
        if address_match:
            updates["address"] = address_match.group(1).strip().title()
        elif self._looks_like_address(message):
            updates["address"] = message.strip().title()

        replace_match = re.search(r"(?:change|set|update)\s+toppings?\s+(?:to|with)\s+(.+)", m)
        if replace_match:
            replacement_text = replace_match.group(1)
            replacement = [
                topping for topping in self.TOPPING_VOCAB if re.search(rf"\b{re.escape(topping)}\b", replacement_text)
            ]
            if replacement:
                updates["replace_toppings"] = self._canonicalize_toppings(replacement)

        removed = []
        remove_patterns = [r"remove\s+([a-z\s,]+)", r"without\s+([a-z\s,]+)", r"no\s+([a-z\s,]+)"]
        for pattern in remove_patterns:
            remove_match = re.search(pattern, m)
            if remove_match:
                removed.extend(
                    [
                        topping
                        for topping in self.TOPPING_VOCAB
                        if re.search(rf"\b{re.escape(topping)}\b", remove_match.group(1))
                    ]
                )
        if removed:
            updates["remove_toppings"] = self._canonicalize_toppings(removed)

        picked = [topping for topping in self.TOPPING_VOCAB if re.search(rf"\b{re.escape(topping)}\b", m)]
        if picked and "replace_toppings" not in updates:
            updates["add_toppings"] = self._canonicalize_toppings(picked)

        return updates

    def _canonicalize_toppings(self, toppings: list[str]) -> list[str]:
        canonical = [self.TOPPING_CANONICAL.get(topping, topping) for topping in toppings]
        return sorted(set(canonical))


class BagelPlanner(Planner):
    BREAD_TYPES = {"sesame", "plain", "everything", "whole wheat", "poppy seed"}
    FILLINGS = {"cream cheese", "roast beef", "turkey", "salmon", "avocado", "ham"}
    EXTRAS = {"onion", "tomato", "lettuce", "cucumber", "capers", "jalapeno", "cheese"}
    PAYMENT = {"card", "cash", "swish", "paypal"}
    REQUIRED_FIELD_STEPS = [
        ("bread_type", "ask_bread_type"),
        ("filling", "ask_filling"),
        ("extras", "ask_extras"),
        ("address", "ask_address"),
        ("payment_method", "ask_payment"),
    ]

    def _extract_with_llm(self, message: str, state: PizzaState | BagelState) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(state, BagelState):
            return {}, {"mode": "llm", "success": False, "error": "Invalid state for BagelPlanner"}
        return self.llm.extract_bagel_update(message, state)

    def _fallback_extract_from_text(self, message: str) -> dict[str, Any]:
        m = message.lower()
        updates: dict[str, Any] = {}

        for bread in self.BREAD_TYPES:
            if re.search(rf"\b{re.escape(bread)}\b", m):
                updates["bread_type"] = bread

        for filling in self.FILLINGS:
            if re.search(rf"\b{re.escape(filling)}\b", m):
                updates["filling"] = filling

        payments_map = {
            "credit card": "card",
            "debit card": "card",
            "card": "card",
            "cash": "cash",
            "swish": "swish",
            "paypal": "paypal",
        }
        for key, value in payments_map.items():
            if key in m:
                updates["payment_method"] = value

        if "confirm" in m or "place order" in m or "go ahead" in m:
            updates["confirmed"] = True

        if re.search(r"\b(reject|cancel order|dont place|don't place|not correct)\b", m):
            updates["review_rejected"] = True

        if "accept" in m and "eta" in m:
            updates["approved_eta_override"] = True
        if "override" in m and "eta" in m:
            updates["approved_eta_override"] = True

        allergy_terms = ["nuts", "peanuts", "gluten", "dairy", "lactose"]
        allergies = [term for term in allergy_terms if re.search(rf"\b{term}\b", m)]
        if allergies:
            updates["allergies"] = sorted(set(allergies))

        address_match = re.search(r"(?:deliver to|address is)\s+([a-z0-9][a-z0-9\s,\-]{5,})", m)
        if address_match:
            updates["address"] = address_match.group(1).strip().title()
        elif self._looks_like_address(message):
            updates["address"] = message.strip().title()

        replace_match = re.search(r"(?:change|set|update)\s+extras?\s+(?:to|with)\s+(.+)", m)
        if replace_match:
            replacement_text = replace_match.group(1)
            replacement = [
                extra for extra in self.EXTRAS if re.search(rf"\b{re.escape(extra)}\b", replacement_text)
            ]
            if replacement:
                updates["replace_extras"] = sorted(set(replacement))

        removed = []
        remove_patterns = [r"remove\s+([a-z\s,]+)", r"without\s+([a-z\s,]+)", r"no\s+([a-z\s,]+)"]
        for pattern in remove_patterns:
            remove_match = re.search(pattern, m)
            if remove_match:
                removed.extend(
                    [
                        extra
                        for extra in self.EXTRAS
                        if re.search(rf"\b{re.escape(extra)}\b", remove_match.group(1))
                    ]
                )
        if removed:
            updates["remove_extras"] = sorted(set(removed))

        picked = [extra for extra in self.EXTRAS if re.search(rf"\b{re.escape(extra)}\b", m)]
        if picked and "replace_extras" not in updates:
            updates["add_extras"] = sorted(set(picked))

        return updates
