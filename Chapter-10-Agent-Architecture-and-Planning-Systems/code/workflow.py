from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

InputType = Literal["choice", "text", "boolean"]


class WorkflowAborted(Exception):
    pass


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    return cleaned.strip("_") or "step"


def normalize_boolean(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"y", "yes", "true", "1"}:
        return True
    if lowered in {"n", "no", "false", "0"}:
        return False
    return None


@dataclass
class RuntimeContext:
    ask_input: Callable[[str], str]
    log_feedback: Callable[[str], None]
    log_warn: Callable[[str], None]


StepFn = Callable[[RuntimeContext, dict[str, Any], "WorkflowStep"], None]


@dataclass
class WorkflowStep:
    name: str
    key: str
    fn: StepFn
    choices: list[str] = field(default_factory=list)
    choice_labels: list[str] = field(default_factory=list)
    input_type: InputType = "choice"
    prompt: str = ""


class Workflow:
    def __init__(self, name: str):
        self.name = name
        self.steps: list[WorkflowStep] = []

    def Step(
        self,
        *,
        name: str,
        fn: StepFn | None,
        choices: list[str] | None = None,
        choice_labels: list[str] | None = None,
        choice: str | None = None,
        input_type: str | None = None,
        key: str | None = None,
        prompt: str | None = None,
    ) -> "Workflow":
        if fn is None:
            raise ValueError(f"Step '{name}' must define fn.")

        resolved_key = key or slugify(name)
        resolved_choices = list(choices or [])
        resolved_choice_labels = list(choice_labels or [])
        raw_input_type = input_type or choice or ("choice" if resolved_choices else "text")
        resolved_input_type = raw_input_type.strip().lower()

        if resolved_input_type not in {"choice", "text", "boolean"}:
            raise ValueError(
                f"Step '{name}' has unsupported input type '{resolved_input_type}'. "
                "Supported: choice, text, boolean."
            )

        if resolved_input_type == "choice" and not resolved_choices:
            resolved_input_type = "text"

        if resolved_choice_labels and len(resolved_choice_labels) != len(resolved_choices):
            raise ValueError(
                f"Step '{name}' has {len(resolved_choice_labels)} choice_labels but "
                f"{len(resolved_choices)} choices. They must match."
            )

        self.steps.append(
            WorkflowStep(
                name=name,
                key=resolved_key,
                fn=fn,
                choices=resolved_choices,
                choice_labels=resolved_choice_labels,
                input_type=resolved_input_type,
                prompt=prompt or f"Please provide {name}:",
            )
        )
        return self


def step_done(state: dict[str, Any], step: WorkflowStep) -> bool:
    value = state.get(step.key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def build_checklist(workflow: Workflow, state: dict[str, Any]) -> str:
    lines: list[str] = []
    for step in workflow.steps:
        marker = "x" if step_done(state, step) else " "
        lines.append(f"- [{marker}] {step.name}")
    return "\n".join(lines)


def checklist_progress(workflow: Workflow, state: dict[str, Any]) -> tuple[int, int]:
    total = len(workflow.steps)
    checked = sum(1 for step in workflow.steps if step_done(state, step))
    return checked, total


def ask_for_step_value(ctx: RuntimeContext, step: WorkflowStep) -> Any:
    if step.input_type == "boolean":
        while True:
            raw = ctx.ask_input(f"{step.prompt} (yes/no)")
            parsed = normalize_boolean(raw)
            if parsed is not None:
                return parsed
            ctx.log_warn("Please answer with yes or no.")

    if step.input_type == "choice" and step.choices:
        if step.choice_labels:
            options = ", ".join(
                f"{i + 1}) {step.choice_labels[i]}" for i in range(len(step.choices))
            )
        else:
            options = ", ".join(f"{i + 1}) {opt}" for i, opt in enumerate(step.choices))
        ctx.log_feedback(f"Choices: {options}")
        while True:
            raw = ctx.ask_input(step.prompt)
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(step.choices):
                    return step.choices[idx]
            if step.choice_labels:
                for i, label in enumerate(step.choice_labels):
                    if raw.strip().lower() == label.lower():
                        return step.choices[i]
            for option in step.choices:
                if raw.strip().lower() == option.lower():
                    return option
            ctx.log_warn("Please choose a valid option number or name.")

    return ctx.ask_input(step.prompt)


def run_workflow(workflow: Workflow, state: dict[str, Any], ctx: RuntimeContext) -> None:
    step_number = 0

    while True:
        checked, total = checklist_progress(workflow, state)
        ctx.log_feedback(f"Progress: {checked}/{total} checklist items completed.")
        print(build_checklist(workflow, state))

        if checked == total:
            ctx.log_feedback(f"Goal achieved. {workflow.name} workflow is complete.")
            return

        next_step: WorkflowStep | None = None
        for step in workflow.steps:
            if not step_done(state, step):
                next_step = step
                break

        if next_step is None:
            ctx.log_feedback(f"Goal achieved. {workflow.name} workflow is complete.")
            return

        step_number += 1
        ctx.log_feedback(f"Step {step_number}: {next_step.key}.")
        next_step.fn(ctx, state, next_step)
