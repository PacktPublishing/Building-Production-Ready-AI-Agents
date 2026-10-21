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


def test_budget_constraints_helpers():
    with local_modules():
        solution = importlib.import_module("solution")

        total = solution.estimate_trip_cost(flight_usd=600, hotel_nights=6, hotel_per_night=150)
        assert total == 1500

        within, within_reason = solution.enforce_budget(solution.BudgetPolicy(max_total_usd=1600), total)
        over, over_reason = solution.enforce_budget(solution.BudgetPolicy(max_total_usd=1400), total)

        assert within is True
        assert "Within budget" in within_reason
        assert over is False
        assert "Over budget" in over_reason
