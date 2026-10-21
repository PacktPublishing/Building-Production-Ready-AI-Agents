from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app_models import BagelState, PizzaState, Session
from execution import BagelExecutor, PizzaExecutor, Monitor
from ollama_client import OllamaClient
from planner import BagelPlanner, PizzaPlanner


class PizzaAgent:
    def __init__(self) -> None:
        self.llm = OllamaClient()
        self.planner = PizzaPlanner(self.llm)
        self.executor = PizzaExecutor()
        self.monitor = Monitor()

    def run_turn(self, session: Session, user_message: str) -> str:
        updates, extraction_meta = self.planner.extract_user_updates(user_message, session.state)
        clarification_reply = self._build_extraction_clarification(session.state, user_message, updates, extraction_meta)
        if clarification_reply is not None:
            session.trace.append(
                {
                    "user_message": user_message,
                    "extraction": extraction_meta,
                    "interpreted_updates": updates,
                    "missing_requirements": self.planner.missing_requirements(session.state),
                    "next_step": "clarify_extraction",
                    "plan": [],
                    "events": [],
                    "state": asdict(session.state),
                }
            )
            return clarification_reply

        self._apply_updates(session.state, updates)

        plan = self.planner.build_plan(session.state)
        reply, events = self.monitor.oversee(plan, session.state, self.executor)
        missing = self.planner.missing_requirements(session.state)
        next_step = plan[0].name if plan else "none"

        session.trace.append(
            {
                "user_message": user_message,
                "extraction": extraction_meta,
                "interpreted_updates": updates,
                "missing_requirements": missing,
                "next_step": next_step,
                "plan": [asdict(step) for step in plan],
                "events": events,
                "state": asdict(session.state),
            }
        )

        return self.llm.rewrite_reply(reply)

    def _build_extraction_clarification(
        self,
        state: PizzaState,
        user_message: str,
        updates: dict[str, Any],
        extraction_meta: dict[str, Any],
    ) -> str | None:
        if updates:
            return None

        stripped = user_message.strip()
        if not stripped:
            return None

        if extraction_meta.get("success") is False:
            if state.size is None:
                return "I could not extract the pizza size from that message. Please reply with one of: small, medium, or large."
            if state.crust is None:
                return "I could not extract the crust from that message. Please reply with one of: thin, thick, gluten-free, or stuffed."
            if not state.toppings:
                return "I could not extract any toppings from that message. Try something like: olives and paprika."
            if state.address is None:
                return "I could not extract the delivery address from that message. Try: address is 10 Main St, NY."
            if state.payment_method is None:
                return "I could not extract the payment method from that message. Please reply with: card, cash, swish, or paypal."

            return "I could not extract any order changes from that message. Please try again with a more explicit update."

        return None

    def _apply_updates(self, state: PizzaState, updates: dict[str, Any]) -> None:
        order_changed = False

        if "size" in updates:
            state.size = updates["size"]
            order_changed = True
        if "crust" in updates:
            state.crust = updates["crust"]
            order_changed = True
        if "payment_method" in updates:
            state.payment_method = updates["payment_method"]
            order_changed = True
        if "address" in updates:
            state.address = updates["address"]
            order_changed = True
        if "allergies" in updates:
            state.allergies = sorted(set(state.allergies + updates["allergies"]))
            order_changed = True
        if "replace_toppings" in updates:
            state.toppings = sorted(set(updates["replace_toppings"]))
            order_changed = True
        if "add_toppings" in updates:
            merged = sorted(set(state.toppings + updates["add_toppings"]))
            state.toppings = merged
            order_changed = True
        if "remove_toppings" in updates:
            state.toppings = [t for t in state.toppings if t not in set(updates["remove_toppings"])]
            order_changed = True
        if "approved_eta_override" in updates:
            state.approved_eta_override = updates["approved_eta_override"]
        if "confirmed" in updates:
            state.confirmed = updates["confirmed"]
            state.review_rejected = False
        if "review_rejected" in updates:
            state.review_rejected = updates["review_rejected"]
            state.confirmed = False

        if order_changed:
            state.confirmed = False
            state.review_rejected = False


class BagelAgent:
    def __init__(self) -> None:
        self.llm = OllamaClient()
        self.planner = BagelPlanner(self.llm)
        self.executor = BagelExecutor()
        self.monitor = Monitor()

    def run_turn(self, session: Session, user_message: str) -> str:
        if not isinstance(session.state, BagelState):
            session.state = BagelState()

        updates, extraction_meta = self.planner.extract_user_updates(user_message, session.state)
        clarification_reply = self._build_extraction_clarification(session.state, user_message, updates, extraction_meta)
        if clarification_reply is not None:
            session.trace.append(
                {
                    "user_message": user_message,
                    "extraction": extraction_meta,
                    "interpreted_updates": updates,
                    "missing_requirements": self.planner.missing_requirements(session.state),
                    "next_step": "clarify_extraction",
                    "plan": [],
                    "events": [],
                    "state": asdict(session.state),
                }
            )
            return clarification_reply

        self._apply_updates(session.state, updates)

        plan = self.planner.build_plan(session.state)
        reply, events = self.monitor.oversee(plan, session.state, self.executor)
        missing = self.planner.missing_requirements(session.state)
        next_step = plan[0].name if plan else "none"

        session.trace.append(
            {
                "user_message": user_message,
                "extraction": extraction_meta,
                "interpreted_updates": updates,
                "missing_requirements": missing,
                "next_step": next_step,
                "plan": [asdict(step) for step in plan],
                "events": events,
                "state": asdict(session.state),
            }
        )

        return self.llm.rewrite_reply(reply)

    def _build_extraction_clarification(
        self,
        state: BagelState,
        user_message: str,
        updates: dict[str, Any],
        extraction_meta: dict[str, Any],
    ) -> str | None:
        if updates:
            return None

        stripped = user_message.strip()
        if not stripped:
            return None

        if extraction_meta.get("success") is False:
            if state.bread_type is None:
                return "I could not extract the bagel bread type. Please reply with one of: sesame, plain, everything, whole wheat, or poppy seed."
            if state.filling is None:
                return "I could not extract the bagel filling. Try one of: cream cheese, roast beef, turkey, salmon, avocado, or ham."
            if not state.extras:
                return "I could not extract any extras from that message. Try: onion and capers."
            if state.address is None:
                return "I could not extract the delivery address. Try: address is 10 Main St, NY."
            if state.payment_method is None:
                return "I could not extract the payment method. Please reply with: card, cash, swish, or paypal."

            return "I could not extract any order changes from that message. Please try again with a more explicit update."

        return None

    def _apply_updates(self, state: BagelState, updates: dict[str, Any]) -> None:
        order_changed = False

        if "bread_type" in updates:
            state.bread_type = updates["bread_type"]
            order_changed = True
        if "filling" in updates:
            state.filling = updates["filling"]
            order_changed = True
        if "payment_method" in updates:
            state.payment_method = updates["payment_method"]
            order_changed = True
        if "address" in updates:
            state.address = updates["address"]
            order_changed = True
        if "allergies" in updates:
            state.allergies = sorted(set(state.allergies + updates["allergies"]))
            order_changed = True
        if "replace_extras" in updates:
            state.extras = sorted(set(updates["replace_extras"]))
            order_changed = True
        if "add_extras" in updates:
            state.extras = sorted(set(state.extras + updates["add_extras"]))
            order_changed = True
        if "remove_extras" in updates:
            state.extras = [t for t in state.extras if t not in set(updates["remove_extras"])]
            order_changed = True
        if "approved_eta_override" in updates:
            state.approved_eta_override = updates["approved_eta_override"]
        if "confirmed" in updates:
            state.confirmed = updates["confirmed"]
            state.review_rejected = False
        if "review_rejected" in updates:
            state.review_rejected = updates["review_rejected"]
            state.confirmed = False

        if order_changed:
            state.confirmed = False
            state.review_rejected = False
