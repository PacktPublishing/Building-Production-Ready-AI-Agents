from __future__ import annotations

import re
import time
from typing import Any, Callable

from workflow import RuntimeContext, Workflow, WorkflowStep, ask_for_step_value


FLIGHT_OPTIONS: list[tuple[str, str]] = [
    ("1", "Morning flight"),
    ("2", "Afternoon flight"),
    ("3", "Evening flight"),
]

HOTEL_OPTIONS: list[tuple[str, str]] = [
    ("1", "Budget stay"),
    ("2", "Boutique hotel"),
    ("3", "City center hotel"),
]

CAR_OPTIONS: list[tuple[str, str]] = [
    ("1", "Economy"),
    ("2", "SUV"),
    ("3", "Luxury"),
]


def search_flights(destination: str, month: str) -> str:
    return (
        f"Found flight options to {destination} in {month}: "
        "1) Morning flight, 2) Afternoon flight, 3) Evening flight."
    )


def book_flight(option: str) -> str:
    return f"Flight booked successfully with option '{option}'."


def get_hotel_info(destination: str, month: str) -> str:
    return (
        f"Found hotel options in {destination} in {month}: "
        "1) Budget stay, 2) Boutique hotel, 3) City center hotel."
    )


def book_hotel(option: str) -> str:
    return f"Hotel booked successfully with option '{option}'."


def book_car(option: str) -> str:
    return f"Rental car booked successfully with option '{option}'."


def create_itinerary(destination: str, days: int = 4) -> str:
    return (
        f"Created a {days}-day itinerary for {destination}: "
        "Day 1 museums, Day 2 landmarks, Day 3 food tour, Day 4 shopping."
    )


def _run_tool(ctx: RuntimeContext, tool_name: str, func: Callable[..., str], **params: str) -> str:
    ctx.log_feedback(f"Step action: tool='{tool_name}' params={params}")
    start = time.perf_counter()
    result = func(**params)
    elapsed = time.perf_counter() - start
    ctx.log_feedback(f"Observation: tool '{tool_name}' finished in {elapsed:.1f}s.")
    ctx.log_feedback(f"Observation: {result}")
    return result


def build_choice_prompt(question: str, options: list[tuple[str, str]]) -> str:
    choice_text = ", ".join(f"{idx + 1}) {label}" for idx, (_, label) in enumerate(options))
    return f"{question} {choice_text}"


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
        kwargs["prompt"] = build_choice_prompt(str(step_def.get("question", "Please choose:")), options)

    return kwargs


def collect_value(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    state[step.key] = ask_for_step_value(ctx, step)


def search_trip_flights(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("destination") or not state.get("month"):
        ctx.log_warn("Cannot search flights yet. Destination and month are required.")
        return
    state[step.key] = _run_tool(
        ctx,
        "search_flights",
        search_flights,
        destination=str(state["destination"]),
        month=str(state["month"]),
    )


def select_flight(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    options_text = str(state.get("search_flights", "")).strip()
    if not options_text:
        ctx.log_warn("Cannot select flight before searching flights.")
        return
    print(options_text)
    state[step.key] = ask_for_step_value(ctx, step)


def book_selected_flight(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    option = str(state.get("select_flight", "")).strip()
    if not option:
        ctx.log_warn("Cannot book a flight without an explicit selected option.")
        return
    _run_tool(ctx, "book_flight", book_flight, option=option)
    state[step.key] = True


def search_hotels(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("destination") or not state.get("month"):
        ctx.log_warn("Cannot search hotels yet. Destination and month are required.")
        return
    state[step.key] = _run_tool(
        ctx,
        "get_hotel_info",
        get_hotel_info,
        destination=str(state["destination"]),
        month=str(state["month"]),
    )


def select_hotel(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    options_text = str(state.get("search_hotels", "")).strip()
    if not options_text:
        ctx.log_warn("Cannot select hotel before searching hotels.")
        return
    print(options_text)
    state[step.key] = ask_for_step_value(ctx, step)


def book_selected_hotel(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    option = str(state.get("select_hotel", "")).strip()
    if not option:
        ctx.log_warn("Cannot book a hotel without an explicit selected option.")
        return
    _run_tool(ctx, "book_hotel", book_hotel, option=option)
    state[step.key] = True


def book_selected_car(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    option = str(state.get("select_car", "")).strip()
    if not option:
        ctx.log_warn("Cannot book a car without an explicit selected option.")
        return
    _run_tool(ctx, "book_car", book_car, option=option)
    state[step.key] = True


def create_trip_itinerary(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("book_flight") or not state.get("book_hotel") or not state.get("book_car"):
        ctx.log_warn("Create itinerary comes after flight, hotel, and car are booked.")
        return
    itinerary = _run_tool(
        ctx,
        "create_itinerary",
        create_itinerary,
        destination=str(state.get("destination", "")),
        days=int(state.get("days", 4)),
    )
    state["itinerary_text"] = itinerary
    state[step.key] = True


TRIP_STEP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "destination",
        "key": "destination",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "Where are you traveling?",
    },
    {
        "name": "travel month",
        "key": "month",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "Which month?",
    },
    {
        "name": "search flights",
        "key": "search_flights",
        "fn": search_trip_flights,
    },
    {
        "name": "select flight",
        "key": "select_flight",
        "fn": select_flight,
        "question": "Which flight option do you want to book?",
        "options": FLIGHT_OPTIONS,
    },
    {
        "name": "book flight",
        "key": "book_flight",
        "fn": book_selected_flight,
    },
    {
        "name": "search hotels",
        "key": "search_hotels",
        "fn": search_hotels,
    },
    {
        "name": "select hotel",
        "key": "select_hotel",
        "fn": select_hotel,
        "question": "Which hotel option do you want to book?",
        "options": HOTEL_OPTIONS,
    },
    {
        "name": "select car",
        "key": "select_car",
        "fn": collect_value,
        "question": "Which car would you like?",
        "options": CAR_OPTIONS,
    },
    {
        "name": "book hotel",
        "key": "book_hotel",
        "fn": book_selected_hotel,
    },
    {
        "name": "book car",
        "key": "book_car",
        "fn": book_selected_car,
    },
    {
        "name": "create itinerary",
        "key": "create_itinerary",
        "fn": create_trip_itinerary,
    },
]


def build_workflow() -> Workflow:
    workflow = Workflow(name="book_trip")
    for step_def in TRIP_STEP_DEFINITIONS:
        workflow.Step(**step_kwargs_from_definition(step_def))
    return workflow


def initialize_state(user_input: str, llm_json: Callable[[list[dict], dict, str], dict]) -> dict[str, Any]:
    content = llm_json(
        [
            {
                "role": "system",
                "content": "Extract trip facts. Return empty strings for missing values.",
            },
            {"role": "user", "content": user_input},
        ],
        {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "month": {"type": "string"},
                "days": {"type": "integer"},
            },
            "required": ["destination", "month", "days"],
        },
        "trip fact extraction",
    )

    days = content.get("days", 4)
    if not isinstance(days, int) or days <= 0:
        days = 4

    return {
        "destination": str(content.get("destination", "")).strip(),
        "month": str(content.get("month", "")).strip(),
        "days": days,
        "search_flights": "",
        "select_flight": "",
        "book_flight": False,
        "search_hotels": "",
        "select_hotel": "",
        "book_hotel": False,
        "select_car": "",
        "book_car": False,
        "create_itinerary": False,
        "itinerary_text": "",
    }


FLIGHT_OPTION_LABELS = dict(FLIGHT_OPTIONS)

HOTEL_OPTION_LABELS = dict(HOTEL_OPTIONS)

CAR_OPTION_LABELS = dict(CAR_OPTIONS)


def option_label(option: str, labels: dict[str, str], fallback: str) -> str:
    if not option:
        return fallback
    return labels.get(str(option).strip(), fallback)


def parse_itinerary_days(itinerary_text: str) -> list[str]:
    if not itinerary_text:
        return []

    day_matches = re.findall(r"(Day\s+\d+[^,.]*(?:[^\n]*))", itinerary_text)
    if day_matches:
        return [match.strip().rstrip(".") for match in day_matches]

    if ":" in itinerary_text:
        _, details = itinerary_text.split(":", 1)
        parts = [part.strip().rstrip(".") for part in details.split(",") if part.strip()]
        return parts

    return [itinerary_text.strip().rstrip(".")]


def render_summary(state: dict[str, Any], bold: Callable[[str], str], highlight: Callable[[str], str]) -> str:
    trip_length = f"{max(int(state.get('days', 4)), 1)} days"
    lines = [
        bold("✈️  Trip Itinerary"),
        bold("================="),
        "",
        bold("📍 Trip Details"),
        f"Destination: {highlight(str(state.get('destination') or 'Not provided'))}",
        f"Travel Date: {highlight(str(state.get('month') or 'Not provided'))}",
        f"Length: {highlight(trip_length)}",
        "",
        bold("🎯 Your Selections"),
        f"Flight: {highlight(option_label(str(state.get('select_flight', '')), FLIGHT_OPTION_LABELS, 'Not selected'))}",
        f"Hotel: {highlight(option_label(str(state.get('select_hotel', '')), HOTEL_OPTION_LABELS, 'Not selected'))}",
        f"Car: {highlight(option_label(str(state.get('select_car', '')), CAR_OPTION_LABELS, 'Not selected'))}",
    ]

    day_lines = parse_itinerary_days(str(state.get("itinerary_text", "")))
    if day_lines:
        lines.extend(["", bold("🗓️  Suggested Plan")])
        for day_line in day_lines:
            lines.append(f"• {day_line}")

    return "\n".join(lines)
