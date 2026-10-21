"""Where to put this:
- Function belongs in `main.py` (or `extensions_setup.py`)
- Call `apply_contextual_hitl(executor)` right after creating `Executor`
- It dynamically rewires `build_itinerary` behavior in `executor.py`
"""

from pathlib import Path
import sys

# Keep this bootstrap only if you run this file directly.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from executor import Executor
from models import StepPolicy


# Place this helper in `main.py` (or `extensions_setup.py`).
def apply_contextual_hitl(executor: Executor) -> None:
    # This references the existing handler from `executor.py`.
    handler = executor.tool_handlers["build_itinerary"]

    # This wrapper is the code part that customizes behavior by step context.
    def wrapped(step, plan):
        trip_type = step.params.get("trip_type", "weekend")
        if trip_type == "1 week":
            executor.register_tool_handler(
                "build_itinerary",
                handler,
                StepPolicy(requires_approval=True, approval_prompt="Approve 7-day itinerary generation?"),
            )
        else:
            executor.register_tool_handler("build_itinerary", handler, StepPolicy())
        return handler(step, plan)

    # Register in the same place you initialize other extension hooks.
    executor.register_tool_handler("build_itinerary", wrapped, StepPolicy())
