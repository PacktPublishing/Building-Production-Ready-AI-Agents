from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import types
import time

from ollama import ChatResponse
from ollama import chat

from workflow import RuntimeContext, WorkflowAborted, run_workflow


OLLAMA_MODEL = "mistral"
VERBOSE = False

RESET = "\033[0m"
BOLD = "\033[1m"
COLORS = {
    "user": "\033[96m",
    "feedback": "\033[93m",
    "verbose": "\033[95m",
    "success": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[91m",
    "choice": "\033[97m",
}


def bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


def highlight_value(text: str) -> str:
    return f"{BOLD}{COLORS['choice']}{text}{RESET}"


def log_user(message: str) -> None:
    print(f"{COLORS['user']}User>{RESET} {message}")


def log_feedback(message: str) -> None:
    print(f"{COLORS['feedback']}Agent>{RESET} {message}")


def log_verbose(message: str) -> None:
    if VERBOSE:
        print(f"{COLORS['verbose']}Agent>{RESET} {message}")


def log_success(message: str) -> None:
    print(f"{COLORS['success']}Agent>{RESET} {message}")


def log_warn(message: str) -> None:
    print(f"{COLORS['warn']}Agent>{RESET} {message}")


def log_error(message: str) -> None:
    print(f"{COLORS['error']}Agent>{RESET} {message}")


def get_user_input(prompt: str) -> str:
    log_feedback(f"User input needed: {prompt}")
    value = input(f"{COLORS['user']}User Input>{RESET} ").strip()
    if value.lower() in {"abort", "cancel", "quit", "exit"}:
        raise WorkflowAborted("User chose to abort the workflow.")
    return value


def llm_json(messages: list[dict], schema: dict, phase: str) -> dict:
    log_verbose(f"Thinking ({phase}) with model '{OLLAMA_MODEL}'...")
    start = time.perf_counter()
    response: ChatResponse = chat(model=OLLAMA_MODEL, messages=messages, format=schema)
    elapsed = time.perf_counter() - start
    log_verbose(f"Finished thinking ({phase}) in {elapsed:.1f}s.")
    return json.loads(response.message.content)


def classify_workflow(user_input: str) -> str:
    content = llm_json(
        [
            {
                "role": "system",
                "content": (
                    "Classify the user's request into one workflow. "
                    "Valid workflow values are 'book_trip' and 'order_pizza'."
                ),
            },
            {"role": "user", "content": user_input},
        ],
        {
            "type": "object",
            "properties": {"workflow": {"type": "string"}},
            "required": ["workflow"],
        },
        "workflow classification",
    )
    return str(content.get("workflow", "")).strip().lower()


def load_module(file_name: str, module_name: str) -> types.ModuleType:
    path = pathlib.Path(__file__).with_name(file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_workflows() -> dict[str, types.ModuleType]:
    trip_module = load_module("trip-booking-workflow.py", "trip_booking_workflow")
    pizza_module = load_module("pizza-workflow.py", "pizza_workflow")
    return {
        "book_trip": trip_module,
        "order_pizza": pizza_module,
    }


def run_agent(user_input: str) -> None:
    workflow_modules = load_workflows()

    log_user(user_input)
    log_feedback("Progress: classifying request into a workflow.")
    workflow_name = classify_workflow(user_input)

    if workflow_name not in workflow_modules:
        log_error("Unsupported workflow from model. Try a trip-planning or pizza-ordering request.")
        return

    selected = workflow_modules[workflow_name]
    workflow = selected.build_workflow()
    log_success(f"Workflow selected: {workflow.name}")

    state = selected.initialize_state(user_input, llm_json)
    ctx = RuntimeContext(
        ask_input=get_user_input,
        log_feedback=log_feedback,
        log_warn=log_warn,
    )

    try:
        run_workflow(workflow, state, ctx)
    except WorkflowAborted as error:
        log_warn(str(error))
        return

    print(selected.render_summary(state, bold, highlight_value))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workflow-first LLM agent")
    parser.add_argument(
        "--prompt",
        default="I need to plan a trip to Paris next month.",
        help="User prompt to run through the agent",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show additional diagnostic logs",
    )
    args = parser.parse_args()

    VERBOSE = args.verbose
    run_agent(args.prompt)
