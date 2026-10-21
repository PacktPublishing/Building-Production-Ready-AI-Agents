from __future__ import annotations

import time
from typing import Any, Callable

from workflow import RuntimeContext, Workflow, WorkflowStep, ask_for_step_value


PIZZA_TYPES: list[tuple[str, str]] = [
    ("margherita", "Margherita"),
    ("pepperoni", "Pepperoni"),
    ("veggie", "Veggie"),
    ("hawaiian", "Hawaiian"),
]

CRUST_TYPES: list[tuple[str, str]] = [
    ("thin", "Thin crust"),
    ("classic", "Classic crust"),
    ("stuffed", "Stuffed crust"),
]

TOPPING_OPTIONS: list[tuple[str, str]] = [
    ("mushrooms", "Mushrooms"),
    ("onions", "Onions"),
    ("olives", "Olives"),
    ("jalapenos", "Jalapenos"),
]

SIZE_OPTIONS: list[tuple[str, str]] = [
    ("small", "Small"),
    ("medium", "Medium"),
    ("large", "Large"),
]

PAYMENT_OPTIONS: list[tuple[str, str]] = [
    ("card", "Card"),
    ("cash", "Cash"),
    ("mobile", "Mobile payment"),
]


def get_pizza_menu() -> str:
    return "Available pizzas: " + ", ".join(label.lower() for _, label in PIZZA_TYPES) + "."


def place_pizza_order(
    pizza_type: str,
    crust: str,
    toppings: str,
    size: str,
    payment: str,
    delivery_address: str,
) -> str:
    return (
        f"Pizza order placed: {size} {pizza_type} pizza with {crust} crust and {toppings}. "
        f"Payment method: {payment}. Delivery to: {delivery_address}."
    )


def _run_tool(ctx: RuntimeContext, tool_name: str, func: Callable[..., str], **params: str) -> str:
    ctx.log_feedback(f"Step action: tool='{tool_name}' params={params}")
    start = time.perf_counter()
    result = func(**params)
    elapsed = time.perf_counter() - start
    ctx.log_feedback(f"Observation: tool '{tool_name}' finished in {elapsed:.1f}s.")
    ctx.log_feedback(f"Observation: {result}")
    return result


def build_choice_prompt(question: str, options: list[tuple[str, str]], *, numbered: bool = True) -> str:
    if numbered:
        options_text = ", ".join(f"{idx + 1}) {label}" for idx, (_, label) in enumerate(options))
    else:
        options_text = ", ".join(label for _, label in options)
    return f"{question} {options_text}"


def step_kwargs_from_definition(step_def: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": step_def["name"],
        "key": step_def["key"],
        "fn": step_def["fn"],
    }

    input_type = str(step_def.get("input_type", "")).strip().lower()
    if input_type:
        kwargs["choice"] = input_type

    options: list[tuple[str, str]] = list(step_def.get("options", []))
    if options and input_type != "text":
        kwargs["choices"] = [value for value, _ in options]
        kwargs["choice_labels"] = [label for _, label in options]

    if "prompt" in step_def:
        kwargs["prompt"] = step_def["prompt"]
    elif options:
        numbered = input_type != "text"
        kwargs["prompt"] = build_choice_prompt(str(step_def.get("question", "Please choose:")), options, numbered=numbered)

    return kwargs


def collect_value(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    state[step.key] = ask_for_step_value(ctx, step)


def select_pizza_type(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("menu_shown"):
        _run_tool(ctx, "get_pizza_menu", get_pizza_menu)
        state["menu_shown"] = True
    state[step.key] = ask_for_step_value(ctx, step)


def place_order(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    missing = [
        key
        for key in ["pizza_type", "crust_type", "toppings", "sizes", "payment", "delivery_address"]
        if not state.get(key)
    ]
    if missing:
        ctx.log_warn(f"Cannot place order yet. Missing: {', '.join(missing)}")
        return

    _run_tool(
        ctx,
        "place_pizza_order",
        place_pizza_order,
        pizza_type=str(state["pizza_type"]),
        crust=str(state["crust_type"]),
        toppings=str(state["toppings"]),
        size=str(state["sizes"]),
        payment=str(state["payment"]),
        delivery_address=str(state["delivery_address"]),
    )
    state[step.key] = True


PIZZA_STEP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "pizza type",
        "key": "pizza_type",
        "fn": select_pizza_type,
        "question": "Which pizza type would you like?",
        "options": PIZZA_TYPES,
    },
    {
        "name": "crust type",
        "key": "crust_type",
        "fn": collect_value,
        "question": "Which crust type?",
        "options": CRUST_TYPES,
    },
    {
        "name": "toppings",
        "key": "toppings",
        "fn": collect_value,
        "input_type": "text",
        "question": "Which toppings? You can pick one or more:",
        "options": TOPPING_OPTIONS,
    },
    {
        "name": "sizes",
        "key": "sizes",
        "fn": collect_value,
        "question": "What size?",
        "options": SIZE_OPTIONS,
    },
    {
        "name": "payment",
        "key": "payment",
        "fn": collect_value,
        "question": "How would you like to pay?",
        "options": PAYMENT_OPTIONS,
    },
    {
        "name": "delivery address",
        "key": "delivery_address",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "Delivery address?",
    },
    {
        "name": "place order",
        "key": "order_placed",
        "fn": place_order,
    },
]


def build_workflow() -> Workflow:
    workflow = Workflow(name="order_pizza")
    for step_def in PIZZA_STEP_DEFINITIONS:
        workflow.Step(**step_kwargs_from_definition(step_def))
    return workflow


def initialize_state(user_input: str, llm_json: Callable[[list[dict], dict, str], dict]) -> dict[str, Any]:
    content = llm_json(
        [
            {
                "role": "system",
                "content": "Extract pizza order facts. Return empty strings for missing values.",
            },
            {"role": "user", "content": user_input},
        ],
        {
            "type": "object",
            "properties": {
                "pizza_type": {"type": "string"},
                "crust_type": {"type": "string"},
                "toppings": {"type": "string"},
                "sizes": {"type": "string"},
                "payment": {"type": "string"},
                "delivery_address": {"type": "string"},
            },
            "required": [
                "pizza_type",
                "crust_type",
                "toppings",
                "sizes",
                "payment",
                "delivery_address",
            ],
        },
        "pizza fact extraction",
    )

    return {
        "menu_shown": False,
        "pizza_type": str(content.get("pizza_type", "")).strip(),
        "crust_type": str(content.get("crust_type", "")).strip(),
        "toppings": str(content.get("toppings", "")).strip(),
        "sizes": str(content.get("sizes", "")).strip(),
        "payment": str(content.get("payment", "")).strip(),
        "delivery_address": str(content.get("delivery_address", "")).strip(),
        "order_placed": False,
    }


def render_summary(state: dict[str, Any], bold: Callable[[str], str], highlight: Callable[[str], str]) -> str:
    return "\n".join(
        [
            bold("🍕 Pizza Order Summary"),
            bold("====================="),
            "",
            f"Pizza: {highlight(str(state.get('pizza_type') or 'Not selected'))}",
            f"Crust: {highlight(str(state.get('crust_type') or 'Not selected'))}",
            f"Toppings: {highlight(str(state.get('toppings') or 'Not selected'))}",
            f"Size: {highlight(str(state.get('sizes') or 'Not selected'))}",
            f"Payment: {highlight(str(state.get('payment') or 'Not selected'))}",
            f"Delivery: {highlight(str(state.get('delivery_address') or 'Not selected'))}",
        ]
    )
