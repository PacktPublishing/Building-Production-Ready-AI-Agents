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


def test_sets_contextual_hitl_for_week_long_trip():
    with local_modules():
        solution = importlib.import_module("solution")

        class FakeExecutor:
            def __init__(self) -> None:
                self.tool_handlers = {
                    "build_itinerary": lambda step, plan: {"success": "true", "message": "itinerary built"}
                }
                self.step_policies = {}

            def register_tool_handler(self, tool_name, handler, policy):
                self.tool_handlers[tool_name] = handler
                self.step_policies[tool_name] = policy

        class Step:
            def __init__(self, trip_type: str):
                self.params = {"trip_type": trip_type}

        executor = FakeExecutor()
        solution.apply_contextual_hitl(executor)

        wrapped = executor.tool_handlers["build_itinerary"]

        wrapped(Step("1 week"), object())
        week_policy = executor.step_policies["build_itinerary"]
        assert week_policy.requires_approval is True
        assert week_policy.approval_prompt == "Approve 7-day itinerary generation?"

        wrapped(Step("weekend"), object())
        weekend_policy = executor.step_policies["build_itinerary"]
        assert weekend_policy.requires_approval is False
