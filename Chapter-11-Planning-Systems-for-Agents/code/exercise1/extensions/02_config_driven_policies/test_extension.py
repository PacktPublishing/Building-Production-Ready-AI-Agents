from __future__ import annotations

import importlib
import json
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


def test_applies_policy_json_to_existing_handlers(tmp_path: Path):
    with local_modules():
        solution = importlib.import_module("solution")

        class FakeExecutor:
            def __init__(self) -> None:
                self.tool_handlers = {
                    "book_flight": lambda step, plan: {"success": "true", "message": "ok"},
                    "reserve_hotel": lambda step, plan: {"success": "true", "message": "ok"},
                }
                self.step_policies = {}

            def register_tool_handler(self, tool_name, handler, policy):
                self.tool_handlers[tool_name] = handler
                self.step_policies[tool_name] = policy

        policy_file = tmp_path / "policy.json"
        policy_file.write_text(
            json.dumps(
                {
                    "book_flight": {
                        "max_retries": 3,
                        "requires_approval": True,
                        "approval_prompt": "Approve flight booking?",
                    }
                }
            ),
            encoding="utf-8",
        )

        executor = FakeExecutor()
        solution.apply_policies_from_json(executor, str(policy_file))

        policy = executor.step_policies["book_flight"]
        assert policy.max_retries == 3
        assert policy.requires_approval is True
        assert policy.approval_prompt == "Approve flight booking?"
