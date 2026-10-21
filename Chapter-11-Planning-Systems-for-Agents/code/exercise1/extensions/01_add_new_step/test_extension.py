from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

MODULE_NAMES = [
    "solution",
    "models",
    "executor",
    "main",
    "monitor",
    "planner",
    "services",
    "console",
    "tracing",
]


@contextmanager
def local_modules():
    extension_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(extension_dir))
    for name in MODULE_NAMES:
        sys.modules.pop(name, None)

    try:
        yield
    finally:
        for name in MODULE_NAMES:
            sys.modules.pop(name, None)
        if sys.path and sys.path[0] == str(extension_dir):
            sys.path.pop(0)


def test_adds_transfer_step_once_and_registers_handler():
    with local_modules():
        solution = importlib.import_module("solution")
        models = importlib.import_module("models")

        class FakeExecutor:
            def __init__(self) -> None:
                self.tool_handlers = {}
                self.step_policies = {}

            def register_tool_handler(self, tool_name, handler, policy):
                self.tool_handlers[tool_name] = handler
                self.step_policies[tool_name] = policy

        executor = FakeExecutor()
        solution.register_transfer_step(executor, solution.TransferService())
        assert "book_transfer" in executor.tool_handlers

        base_step = models.PlanStep(
            description="Book flight",
            tool="book_flight",
            params={"destination": "London", "start_date": "2026-01-01", "trip_type": "1 week"},
        )
        plan = models.Plan(steps=[base_step], service_name="primary")

        updated = solution.ensure_transfer_step(plan)
        tools = [step.tool for step in updated.steps]
        assert tools.count("book_transfer") == 1

        updated_again = solution.ensure_transfer_step(updated)
        tools_again = [step.tool for step in updated_again.steps]
        assert tools_again.count("book_transfer") == 1
