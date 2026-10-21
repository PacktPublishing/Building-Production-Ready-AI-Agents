from typing import Callable, Dict

from console import (
    Colors,
    agent_print,
    choose_numbered_option,
    colorize,
    error_print,
    warn_print,
)
from models import Plan, PlanStep, RunMetrics, StepPolicy, StepResult
from services import (
    AlternativeTravelService,
    HotelService,
    ItineraryService,
    PrimaryTravelService,
)
from tracing import TraceRecorder


class Executor:
    def __init__(
        self,
        primary_service: PrimaryTravelService,
        alternative_service: AlternativeTravelService,
        hotel_service: HotelService,
        itinerary_service: ItineraryService,
        metrics: RunMetrics,
        trace: TraceRecorder,
    ) -> None:
        self.primary_service = primary_service
        self.alternative_service = alternative_service
        self.hotel_service = hotel_service
        self.itinerary_service = itinerary_service
        self.metrics = metrics
        self.trace = trace
        self.tool_handlers: Dict[str, Callable[[PlanStep, Plan], Dict[str, str]]] = {}
        self.step_policies: Dict[str, StepPolicy] = {}
        self._register_default_handlers_and_policies()

    def _register_default_handlers_and_policies(self) -> None:
        self.register_tool_handler(
            tool_name="book_flight",
            handler=self._handle_book_flight,
            policy=StepPolicy(max_retries=1),
        )
        self.register_tool_handler(
            tool_name="reserve_hotel",
            handler=self._handle_reserve_hotel,
            policy=StepPolicy(),
        )
        self.register_tool_handler(
            tool_name="build_itinerary",
            handler=self._handle_build_itinerary,
            policy=StepPolicy(),
        )

    def register_tool_handler(
        self,
        tool_name: str,
        handler: Callable[[PlanStep, Plan], Dict[str, str]],
        policy: StepPolicy | None = None,
    ) -> None:
        self.tool_handlers[tool_name] = handler
        self.step_policies[tool_name] = policy or StepPolicy()

    def get_step_policy(self, tool_name: str) -> StepPolicy:
        return self.step_policies.get(tool_name, StepPolicy())

    def execute_plan(self, plan: Plan, is_retry: bool = False) -> list[StepResult]:
        if is_retry:
            print(colorize('[EXECUTOR] "Retrying step 1: Book flight - ', Colors.YELLOW), end="")
            self.trace.record("executor", "retry_started")
        else:
            if plan.service_name == "alternative":
                agent_print('[EXECUTOR] "Executing new plan..."')
            else:
                agent_print('[EXECUTOR] "Executing plan..."')
            self.trace.record(
                "executor",
                "execution_started",
                {"service": plan.service_name, "step_count": len(plan.steps)},
            )

        results: list[StepResult] = []

        for index, step in enumerate(plan.steps, start=1):
            if not is_retry:
                agent_print(f'[EXECUTOR] "Starting step {index}/{len(plan.steps)}: {step.description}"')

            policy = self.get_step_policy(step.tool)
            if policy.requires_approval and not is_retry:
                self.metrics.approval_prompts += 1
                approval_choice = choose_numbered_option(
                    policy.approval_prompt or f"Approve step: {step.description}?",
                    ["Approve", "Decline"],
                )
                if approval_choice != 1:
                    response = {
                        "success": "false",
                        "message": f"User declined step approval: {step.tool}",
                    }
                    self.trace.record(
                        "executor",
                        "step_approval_declined",
                        {"tool": step.tool, "description": step.description},
                    )
                else:
                    self.metrics.approval_granted += 1
                    response = self._run_handler(step, plan)
            else:
                response = self._run_handler(step, plan)

            success = response.get("success") == "true"
            message = response.get("message", "Unknown result")
            self.metrics.steps_attempted += 1
            if success:
                self.metrics.steps_succeeded += 1
            else:
                self.metrics.steps_failed += 1

            if is_retry:
                retry_message = "Failed again." if not success else message
                if success:
                    agent_print(f'[EXECUTOR] "{retry_message}"')
                else:
                    error_print(f'[EXECUTOR] "{retry_message}"')
            else:
                step_message = f'[EXECUTOR] "Step {index}: {step.description} - {message}"'
                if success:
                    agent_print(step_message)
                else:
                    error_print(step_message)

            results.append(
                StepResult(
                    description=step.description,
                    tool=step.tool,
                    success=success,
                    message=message,
                    details={
                        "provider": response.get("provider"),
                        "routing": response.get("routing"),
                        "stopovers": response.get("stopovers"),
                        "hotel_name": response.get("hotel_name"),
                        "hotel_area": response.get("hotel_area"),
                        "hotel_price_per_night": response.get("hotel_price_per_night"),
                        "itinerary_summary": response.get("summary"),
                    },
                )
            )

            self.trace.record(
                "executor",
                "step_completed",
                {
                    "index": index,
                    "tool": step.tool,
                    "description": step.description,
                    "success": success,
                    "message": message,
                },
            )

            if not success:
                self.trace.record("executor", "execution_stopped_on_failure", {"failed_step": index})
                break

        return results

    def _run_handler(self, step: PlanStep, plan: Plan) -> Dict[str, str]:
        handler = self.tool_handlers.get(step.tool)
        if handler is None:
            return {
                "success": "false",
                "message": f"Unknown tool: {step.tool}",
            }
        return handler(step, plan)

    def _handle_book_flight(self, step: PlanStep, plan: Plan) -> Dict[str, str]:
        destination = step.params.get("destination", "Paris")
        if plan.service_name == "alternative":
            return self.alternative_service.book_flight(destination)
        return self.primary_service.book_flight(destination)

    def _handle_reserve_hotel(self, step: PlanStep, _plan: Plan) -> Dict[str, str]:
        destination = step.params.get("destination", "Paris")
        hotel_options = self.hotel_service.get_hotel_options(destination)
        selected_hotel = self._select_hotel_option(destination, hotel_options)
        return self.hotel_service.reserve_hotel(destination, selected_hotel)

    def _handle_build_itinerary(self, step: PlanStep, _plan: Plan) -> Dict[str, str]:
        destination = step.params.get("destination", "Paris")
        return self.itinerary_service.build_itinerary(
            destination,
            step.params.get("start_date", ""),
            step.params.get("trip_type", "weekend"),
        )

    def _select_hotel_option(
        self,
        destination: str,
        hotel_options: list[Dict[str, str]],
    ) -> Dict[str, str]:
        warn_print('[MONITOR] "Human-in-the-loop required: choose one of the hotel options."')
        self.metrics.approval_prompts += 1
        self.trace.record(
            "executor",
            "hotel_selection_requested",
            {"destination": destination, "option_count": len(hotel_options)},
        )

        option_labels = [
            f"{hotel['name']} | area={hotel['area']} | price/night={hotel['price_per_night']}"
            for hotel in hotel_options
        ]
        selected_idx = choose_numbered_option("Choose hotel option:", option_labels) - 1
        selected_hotel = hotel_options[selected_idx]
        self.metrics.approval_granted += 1

        self.trace.record(
            "executor",
            "hotel_selected",
            {
                "hotel_name": selected_hotel["name"],
                "area": selected_hotel["area"],
                "price_per_night": selected_hotel["price_per_night"],
            },
        )
        return selected_hotel
