from __future__ import annotations

from typing import Any

from workflow import RuntimeContext, Workflow, WorkflowStep


PIZZA_TYPES = ["margherita", "pepperoni", "veggie", "hawaiian"]
CRUST_TYPES = ["thin", "classic", "stuffed"]
SIZE_OPTIONS = ["small", "medium", "large"]


def build_prompt(question: str, options: list[str]) -> str:
    options_text = ", ".join(f"{idx + 1}) {option}" for idx, option in enumerate(options))
    return f"{question} {options_text}"


def _noop_step(_ctx: RuntimeContext, _state: dict[str, Any], _step: WorkflowStep) -> None:
    return


def build_example_workflow() -> Workflow:
    return (
        Workflow(name="order pizza")
        .Step(
            name="pizza type",
            choices=PIZZA_TYPES,
            fn=_noop_step,
            prompt=build_prompt("Choose pizza type:", PIZZA_TYPES),
        )
        .Step(
            name="crust type",
            choices=CRUST_TYPES,
            fn=_noop_step,
            prompt=build_prompt("Choose crust type:", CRUST_TYPES),
        )
        .Step(
            name="toppings",
            choice="text",
            fn=_noop_step,
            prompt="Choose toppings (comma separated)",
        )
        .Step(
            name="sizes",
            choices=SIZE_OPTIONS,
            fn=_noop_step,
            prompt=build_prompt("Choose size:", SIZE_OPTIONS),
        )
        .Step(name="delivery address", choice="text", fn=_noop_step)
    )