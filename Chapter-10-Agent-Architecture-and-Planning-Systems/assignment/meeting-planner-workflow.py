from __future__ import annotations

import time
from typing import Any, Callable

from workflow import RuntimeContext, Workflow, WorkflowStep, ask_for_step_value


SLOT_OPTIONS: list[tuple[str, str]] = [
    ("1", "09:00"),
    ("2", "11:00"),
    ("3", "14:00"),
    ("4", "16:00"),
]

MEETING_TYPE_OPTIONS: list[tuple[str, str]] = [
    ("virtual", "Virtual"),
    ("in_person", "In person"),
    ("hybrid", "Hybrid"),
]


def suggest_time_slots(date: str, participants: str) -> str:
    return (
        f"Suggested slots for {date} with {participants}: "
        "1) 09:00, 2) 11:00, 3) 14:00, 4) 16:00."
    )


def schedule_meeting(
    title: str,
    date: str,
    participants: str,
    slot: str,
    meeting_type: str,
    duration_minutes: int,
) -> str:
    return (
        f"Meeting scheduled: '{title}' on {date} at {slot} for {duration_minutes} minutes "
        f"({meeting_type}) with {participants}."
    )


def _run_tool(ctx: RuntimeContext, tool_name: str, func: Callable[..., str], **params: Any) -> str:
    ctx.log_feedback(f"Step action: tool='{tool_name}' params={params}")
    start = time.perf_counter()
    result = func(**params)
    elapsed = time.perf_counter() - start
    ctx.log_feedback(f"Observation: tool '{tool_name}' finished in {elapsed:.1f}s.")
    ctx.log_feedback(f"Observation: {result}")
    return result


def build_choice_prompt(question: str, options: list[tuple[str, str]]) -> str:
    options_text = ", ".join(f"{idx + 1}) {label}" for idx, (_, label) in enumerate(options))
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
        kwargs["prompt"] = build_choice_prompt(str(step_def.get("question", "Please choose:")), options)

    return kwargs


def collect_value(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    state[step.key] = ask_for_step_value(ctx, step)


def suggest_slots_for_meeting(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("meeting_date") or not state.get("participants"):
        ctx.log_warn("Cannot suggest slots yet. Meeting date and participants are required.")
        return
    state[step.key] = _run_tool(
        ctx,
        "suggest_time_slots",
        suggest_time_slots,
        date=str(state["meeting_date"]),
        participants=str(state["participants"]),
    )


def select_slot(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not str(state.get("suggest_slots", "")).strip():
        ctx.log_warn("Cannot select a slot before suggestions are generated.")
        return
    print(state["suggest_slots"])
    state[step.key] = ask_for_step_value(ctx, step)


def schedule_selected_meeting(ctx: RuntimeContext, state: dict[str, Any], step: WorkflowStep) -> None:
    if not state.get("slot"):
        ctx.log_warn("Cannot schedule without a selected slot.")
        return

    if not state.get("confirm"):
        ctx.log_warn("Meeting not confirmed yet. Answer yes to confirmation before scheduling.")
        return

    slot_lookup = dict(SLOT_OPTIONS)
    slot_value = slot_lookup.get(str(state["slot"]).strip(), str(state["slot"]).strip())

    _run_tool(
        ctx,
        "schedule_meeting",
        schedule_meeting,
        title=str(state.get("meeting_title", "Team sync")),
        date=str(state.get("meeting_date", "")),
        participants=str(state.get("participants", "")),
        slot=slot_value,
        meeting_type=str(state.get("meeting_type", "virtual")),
        duration_minutes=int(state.get("duration_minutes", 30)),
    )
    state[step.key] = True


MEETING_STEP_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "meeting title",
        "key": "meeting_title",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "What is the meeting title?",
    },
    {
        "name": "meeting date",
        "key": "meeting_date",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "What date should the meeting be on?",
    },
    {
        "name": "participants",
        "key": "participants",
        "input_type": "text",
        "fn": collect_value,
        "prompt": "Who should be invited?",
    },
    {
        "name": "meeting type",
        "key": "meeting_type",
        "fn": collect_value,
        "question": "What meeting type do you want?",
        "options": MEETING_TYPE_OPTIONS,
    },
    {
        "name": "suggest slots",
        "key": "suggest_slots",
        "fn": suggest_slots_for_meeting,
    },
    {
        "name": "select slot",
        "key": "slot",
        "fn": select_slot,
        "question": "Choose a time slot:",
        "options": SLOT_OPTIONS,
    },
    {
        "name": "confirm",
        "key": "confirm",
        "input_type": "boolean",
        "fn": collect_value,
        "prompt": "Confirm this meeting plan?",
    },
    {
        "name": "schedule meeting",
        "key": "meeting_scheduled",
        "fn": schedule_selected_meeting,
    },
]


def build_workflow() -> Workflow:
    workflow = Workflow(name="plan_meeting")
    for step_def in MEETING_STEP_DEFINITIONS:
        workflow.Step(**step_kwargs_from_definition(step_def))
    return workflow


def initialize_state(user_input: str, llm_json: Callable[[list[dict], dict, str], dict]) -> dict[str, Any]:
    content = llm_json(
        [
            {
                "role": "system",
                "content": "Extract meeting planning facts. Return empty strings for missing values.",
            },
            {"role": "user", "content": user_input},
        ],
        {
            "type": "object",
            "properties": {
                "meeting_title": {"type": "string"},
                "meeting_date": {"type": "string"},
                "participants": {"type": "string"},
                "meeting_type": {"type": "string"},
                "duration_minutes": {"type": "integer"},
            },
            "required": [
                "meeting_title",
                "meeting_date",
                "participants",
                "meeting_type",
                "duration_minutes",
            ],
        },
        "meeting fact extraction",
    )

    duration = content.get("duration_minutes", 30)
    if not isinstance(duration, int) or duration <= 0:
        duration = 30

    return {
        "meeting_title": str(content.get("meeting_title", "")).strip(),
        "meeting_date": str(content.get("meeting_date", "")).strip(),
        "participants": str(content.get("participants", "")).strip(),
        "meeting_type": str(content.get("meeting_type", "")).strip() or "virtual",
        "duration_minutes": duration,
        "suggest_slots": "",
        "slot": "",
        "confirm": False,
        "meeting_scheduled": False,
    }


def render_summary(state: dict[str, Any], bold: Callable[[str], str], highlight: Callable[[str], str]) -> str:
    slot_labels = dict(SLOT_OPTIONS)
    selected_slot = slot_labels.get(str(state.get("slot", "")).strip(), "Not selected")

    return "\n".join(
        [
            bold("Meeting Plan Summary"),
            bold("===================="),
            "",
            f"Title: {highlight(str(state.get('meeting_title') or 'Not provided'))}",
            f"Date: {highlight(str(state.get('meeting_date') or 'Not provided'))}",
            f"Participants: {highlight(str(state.get('participants') or 'Not provided'))}",
            f"Type: {highlight(str(state.get('meeting_type') or 'Not provided'))}",
            f"Duration: {highlight(str(state.get('duration_minutes') or 30))} minutes",
            f"Slot: {highlight(selected_slot)}",
            f"Scheduled: {highlight('Yes' if state.get('meeting_scheduled') else 'No')}",
        ]
    )
