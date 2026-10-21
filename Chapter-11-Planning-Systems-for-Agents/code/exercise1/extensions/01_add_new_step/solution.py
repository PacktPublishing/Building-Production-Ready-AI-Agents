"""Where to put this:
- `TransferService`: add to `services.py`
- `register_transfer_step(...)`: call from `main.py` right after creating `Executor`
- Planner step append: add in `planner.py` when constructing `plan.steps`
"""

from pathlib import Path
import sys

# Keep this bootstrap only if you run this file directly.
# Not needed if you copy the snippets into project modules.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from executor import Executor
from models import Plan, PlanStep, StepPolicy


# Place this class in `services.py`.
class TransferService:
    def book_transfer(self, destination: str) -> dict[str, str]:
        return {
            "success": "true",
            "message": f"Booked airport transfer in {destination}.",
            "transfer_provider": "CityRide",
        }


# Place this function in `main.py` (or a dedicated `extensions_setup.py`),
# then call it after the `Executor` instance is created.
def register_transfer_step(executor: Executor, transfer_service: TransferService) -> None:
    # This nested handler is the code part that belongs in `executor.py`
    # if you prefer registering directly inside Executor.
    def handle_transfer(step: PlanStep, _plan):
        destination = step.params.get("destination", "Unknown")
        return transfer_service.book_transfer(destination)

    executor.register_tool_handler(
        tool_name="book_transfer",
        handler=handle_transfer,
        policy=StepPolicy(max_retries=0),
    )


def ensure_transfer_step(plan: Plan) -> Plan:
    if any(step.tool == "book_transfer" for step in plan.steps):
        return plan

    shared_params = dict(plan.steps[0].params) if plan.steps else {}
    plan.steps.append(
        PlanStep(
            description="Book airport transfer",
            tool="book_transfer",
            params=shared_params,
        )
    )
    return plan


# Place this line in `planner.py` where `plan.steps` is assembled:
# plan.steps.append(PlanStep(description="Book airport transfer", tool="book_transfer", params=shared_params))
