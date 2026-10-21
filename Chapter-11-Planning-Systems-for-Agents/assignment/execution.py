from __future__ import annotations

import datetime as dt
import random
import uuid
from abc import ABC, abstractmethod
from typing import Any

from app_models import BagelState, PizzaState, PlanStep, StepResult


class BaseExecutor(ABC):
    OPEN_HOUR = 10
    CLOSE_HOUR = 22

    @abstractmethod
    def execute(self, step: PlanStep, state: PizzaState | BagelState) -> StepResult:
        ...

    def _is_store_open(self) -> bool:
        now_hour = dt.datetime.now().hour
        return self.OPEN_HOUR <= now_hour < self.CLOSE_HOUR

    def _is_deliverable_address(self, address: str | None) -> bool:
        if not address:
            return True
        return "outside" not in address.lower()

    def _store_closed_result(self) -> StepResult:
        return StepResult(
            "blocked",
            "The store is closed right now. We are open between 10:00 and 22:00.",
        )

    def _outside_radius_result(self) -> StepResult:
        return StepResult(
            "blocked",
            "That address seems outside our delivery radius. Please provide another nearby address.",
        )

    def _charge_payment(self, payment_method: str | None) -> StepResult:
        if payment_method == "cash":
            return StepResult("success", "Cash payment selected. Payment will be collected on delivery.")

        if random.random() < 0.1:
            return StepResult(
                "blocked",
                "Payment authorization failed. Please try another payment method.",
            )

        return StepResult("success", "Payment authorized successfully.")


class PizzaExecutor(BaseExecutor):
    ALLOWED_TOPPINGS = {
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
        "paprika",
    }

    def execute(self, step: PlanStep, state: PizzaState | BagelState) -> StepResult:
        if not isinstance(state, PizzaState):
            return StepResult("error", "Invalid state for PizzaExecutor")

        if step.name == "ask_size":
            captured: list[str] = []
            if state.crust:
                captured.append(f"crust {state.crust}")
            if state.toppings:
                captured.append(f"toppings {', '.join(state.toppings)}")
            if state.address:
                captured.append(f"delivery {state.address}")
            if state.payment_method:
                captured.append(f"payment {state.payment_method}")

            prefix = ""
            if captured:
                prefix = f"I captured {', '.join(captured)}. "

            return StepResult(
                "needs_input",
                f"{prefix}What pizza size would you like (small, medium, or large)? "
                "You can include other details in the same message (for example crust, toppings, address, and payment).",
            )
        if step.name == "ask_crust":
            return StepResult("needs_input", "Great. What crust do you want: thin, thick, gluten-free, or stuffed?")
        if step.name == "ask_toppings":
            return StepResult(
                "needs_input",
                "What toppings should I add? For example: pepperoni, mushrooms, olives, jalapeno.",
            )
        if step.name == "ask_address":
            return StepResult(
                "needs_input",
                "What delivery address should we use? Example: NY Place 1, NY",
            )
        if step.name == "ask_payment":
            return StepResult("needs_input", "How would you like to pay: card, cash, swish, or paypal?")

        if step.name == "check_constraints":
            return self._check_constraints(state)

        if step.name == "ask_changes":
            return StepResult(
                "needs_input",
                "Order review rejected. Tell me what to change, or reply with 'confirm' when it looks right.\n"
                "Examples: change crust to thick, change toppings to olives and paprika, remove olives, address is 10 Main St, NY.",
            )

        if step.name == "ask_confirm":
            toppings = ", ".join(state.toppings) if state.toppings else "none"
            return StepResult(
                "needs_input",
                self._format_order_summary(state, toppings),
            )

        if step.name == "charge_payment":
            return self._charge_payment(state.payment_method)

        if step.name == "place_order":
            order_id = f"PZ-{str(uuid.uuid4())[:8].upper()}"
            state.order_id = order_id
            return StepResult("success", f"Order placed successfully. Your order id is {order_id}.")

        return StepResult("error", f"Unknown step: {step.name}")

    def _check_constraints(self, state: PizzaState) -> StepResult:
        if not self._is_store_open():
            return self._store_closed_result()

        if not self._is_deliverable_address(state.address):
            return self._outside_radius_result()

        invalid_toppings = [t for t in state.toppings if t not in self.ALLOWED_TOPPINGS]
        if invalid_toppings:
            return StepResult(
                "blocked",
                f"These toppings are unavailable: {', '.join(invalid_toppings)}. Please pick alternatives.",
            )

        if "nuts" in state.allergies and "pesto" in state.toppings:
            return StepResult("blocked", "Nut allergy conflict detected with pesto. Please remove pesto.")

        if "gluten" in state.allergies and state.crust != "gluten-free":
            return StepResult(
                "blocked",
                "Gluten allergy detected. Please switch crust to gluten-free.",
            )

        eta = 20 + max(0, len(state.toppings) - 2) * 4
        if eta > 45 and not state.approved_eta_override:
            return StepResult(
                "needs_approval",
                f"Estimated delivery time is {eta} minutes, above your max target of 45 minutes. Reply with 'accept eta' to continue or change your order.",
                details={"eta": eta},
            )

        return StepResult("success", "Constraints check passed.")

    def _format_order_summary(self, state: PizzaState, toppings: str) -> str:
        return (
            "Order summary\n"
            f"- Size: {state.size}\n"
            f"- Crust: {state.crust}\n"
            f"- Toppings: {toppings}\n"
            f"- Delivery: {state.address}\n"
            f"- Payment: {state.payment_method}\n"
            "\n"
            "Reply with one of these:\n"
            "- confirm: place the order\n"
            "- reject: stop and let me change it\n"
            "- change ... : update part of the order"
        )


class BagelExecutor(BaseExecutor):
    def execute(self, step: PlanStep, state: PizzaState | BagelState) -> StepResult:
        if not isinstance(state, BagelState):
            return StepResult("error", "Invalid state for BagelExecutor")

        if step.name == "ask_bread_type":
            return StepResult("needs_input", "What bagel bread type would you like: sesame, plain, everything, whole wheat, or poppy seed?")
        if step.name == "ask_filling":
            return StepResult("needs_input", "What filling would you like: cream cheese, roast beef, turkey, salmon, avocado, or ham?")
        if step.name == "ask_extras":
            return StepResult("needs_input", "Any extras? For example onion, tomato, lettuce, cucumber, capers, jalapeno, or cheese.")
        if step.name == "ask_address":
            return StepResult("needs_input", "What delivery address should we use? Example: NY Place 1, NY")
        if step.name == "ask_payment":
            return StepResult("needs_input", "How would you like to pay: card, cash, swish, or paypal?")

        if step.name == "check_constraints":
            return self._check_constraints(state)

        if step.name == "ask_changes":
            return StepResult(
                "needs_input",
                "Order review rejected. Tell me what to change, or reply with 'confirm' when it looks right.\n"
                "Examples: change bread type to sesame, change extras to onion and capers, remove onion, address is 10 Main St, NY.",
            )

        if step.name == "ask_confirm":
            extras = ", ".join(state.extras) if state.extras else "none"
            return StepResult("needs_input", self._format_order_summary(state, extras))

        if step.name == "charge_payment":
            return self._charge_payment(state.payment_method)

        if step.name == "place_order":
            order_id = f"BG-{str(uuid.uuid4())[:8].upper()}"
            state.order_id = order_id
            return StepResult("success", f"Order placed successfully. Your order id is {order_id}.")

        return StepResult("error", f"Unknown step: {step.name}")

    def _check_constraints(self, state: BagelState) -> StepResult:
        if not self._is_store_open():
            return self._store_closed_result()

        if not self._is_deliverable_address(state.address):
            return self._outside_radius_result()

        if "gluten" in state.allergies and state.bread_type != "gluten-free":
            return StepResult("blocked", "Gluten allergy detected. Please choose a gluten-free bread type.")

        eta = 15 + max(0, len(state.extras) - 2) * 3
        if eta > 45 and not state.approved_eta_override:
            return StepResult(
                "needs_approval",
                f"Estimated delivery time is {eta} minutes, above your max target of 45 minutes. Reply with 'accept eta' to continue or change your order.",
                details={"eta": eta},
            )

        return StepResult("success", "Constraints check passed.")

    def _format_order_summary(self, state: BagelState, extras: str) -> str:
        return (
            "Order summary\n"
            f"- Bread type: {state.bread_type}\n"
            f"- Filling: {state.filling}\n"
            f"- Extras: {extras}\n"
            f"- Delivery: {state.address}\n"
            f"- Payment: {state.payment_method}\n"
            "\n"
            "Reply with one of these:\n"
            "- confirm: place the order\n"
            "- reject: stop and let me change it\n"
            "- change ... : update part of the order"
        )


# Backward-compatible alias for existing imports.
Executor = PizzaExecutor


class Monitor:
    def oversee(self, plan: list[PlanStep], state: PizzaState | BagelState, executor: BaseExecutor) -> tuple[str, list[dict[str, Any]]]:
        events: list[dict[str, Any]] = []
        last_message = ""

        for step in plan:
            result = executor.execute(step, state)
            events.append(
                {
                    "step": step.name,
                    "status": result.status,
                    "message": result.message,
                    "details": result.details,
                }
            )
            last_message = result.message

            if result.status in {"needs_input", "needs_approval", "blocked", "error"}:
                break

        return last_message, events
