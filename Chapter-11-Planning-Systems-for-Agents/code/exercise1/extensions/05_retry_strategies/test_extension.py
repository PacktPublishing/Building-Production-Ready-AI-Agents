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


def test_retry_delay_strategies():
    with local_modules():
        solution = importlib.import_module("solution")

        assert solution.get_retry_delays(solution.RetrySpec(strategy="no_retry", attempts=3)) == []
        assert solution.get_retry_delays(solution.RetrySpec(strategy="fixed", attempts=3)) == [1, 1, 1]
        assert solution.get_retry_delays(solution.RetrySpec(strategy="exponential_backoff", attempts=4)) == [1, 2, 4, 8]
        assert solution.get_retry_delays(solution.RetrySpec(strategy="unsupported", attempts=2)) == []
