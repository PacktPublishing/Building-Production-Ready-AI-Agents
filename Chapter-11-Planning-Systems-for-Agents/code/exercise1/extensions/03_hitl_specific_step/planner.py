import json
from datetime import datetime
from typing import Dict, Optional

import ollama

from console import agent_print, warn_print
from models import Plan, PlanStep
from tracing import TraceRecorder


class Planner:
    def __init__(self, client: ollama.Client, model: str, trace: TraceRecorder) -> None:
        self.client = client
        self.model = model
        self.trace = trace
        self.last_prompt: Optional[str] = None
        self.last_destination: Optional[str] = None
        self.last_start_date: Optional[str] = None
        self.last_trip_type: Optional[str] = None

    def generate_plan(
        self,
        user_prompt: str,
        destination: str,
        start_date: str,
        trip_type: str,
        use_alternative_service: bool = False,
    ) -> Plan:
        self.last_prompt = user_prompt
        self.last_destination = destination
        self.last_start_date = start_date
        self.last_trip_type = trip_type
        agent_print('[PLANNER] "Generating plan..."')
        self.trace.record(
            "planner",
            "generate_plan_start",
            {
                "destination": destination,
                "start_date": start_date,
                "trip_type": trip_type,
                "use_alternative_service": use_alternative_service,
            },
        )

        plan_payload = self._call_llm_for_plan(
            user_prompt,
            destination,
            start_date,
            trip_type,
            use_alternative_service,
        )
        service_name = plan_payload.get("service", "alternative" if use_alternative_service else "primary")
        if service_name not in {"primary", "alternative"}:
            service_name = "alternative" if use_alternative_service else "primary"

        step_text = str(
            plan_payload.get(
                "step_description",
                "Book flight with alternative service"
                if service_name == "alternative"
                else "Book flight",
            )
        )

        step_destination = str(plan_payload.get("destination", destination))
        step_start_date = str(plan_payload.get("start_date", start_date))
        step_trip_type = str(plan_payload.get("trip_type", trip_type))

        shared_params = {
            "destination": step_destination,
            "start_date": step_start_date,
            "trip_type": step_trip_type,
        }

        plan = Plan(
            steps=[
                PlanStep(
                    description=step_text,
                    tool="book_flight",
                    params=shared_params,
                ),
                PlanStep(
                    description=f"Reserve hotel in {step_destination}",
                    tool="reserve_hotel",
                    params=shared_params,
                ),
                PlanStep(
                    description=f"Build day-by-day itinerary for {step_destination}",
                    tool="build_itinerary",
                    params=shared_params,
                ),
            ],
            service_name=service_name,
        )

        if use_alternative_service:
            agent_print('[PLANNER] "New plan generated successfully!"')
        else:
            agent_print('[PLANNER] "Plan generated successfully!"')

        self.show_plan(plan)
        self.trace.record(
            "planner",
            "generate_plan_complete",
            {"service": service_name, "step_count": len(plan.steps)},
        )

        return plan

    def replan_for_service_failure(self, feedback: str) -> Plan:
        agent_print(f'[PLANNER] "Received monitor feedback: {feedback}"')
        agent_print('[PLANNER] "Generating new plan with alternative flight booking service..."')
        self.trace.record("planner", "replan_for_service_failure", {"feedback": feedback})
        prompt = self.last_prompt or "Plan a trip for me."
        destination = self.last_destination or "Paris"
        start_date = self.last_start_date or datetime.today().strftime("%Y-%m-%d")
        trip_type = self.last_trip_type or "weekend"
        return self.generate_plan(
            prompt,
            destination=destination,
            start_date=start_date,
            trip_type=trip_type,
            use_alternative_service=True,
        )

    def _call_llm_for_plan(
        self,
        user_prompt: str,
        destination: str,
        start_date: str,
        trip_type: str,
        use_alternative_service: bool,
    ) -> Dict[str, str]:
        service_hint = "alternative" if use_alternative_service else "primary"
        system_prompt = (
            "You are a travel planner. Return strict JSON with keys: "
            "service (primary|alternative), step_description, destination, start_date, trip_type. "
            "Use primary by default unless the caller explicitly asks for alternative."
        )
        user_message = (
            f"User prompt: {user_prompt}\n"
            f"Destination: {destination}\n"
            f"Start date: {start_date}\n"
            f"Trip type: {trip_type}\n"
            f"Service preference: {service_hint}\n"
            "Generate a one-step plan to book a flight."
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                format="json",
            )

            payload = json.loads(response.message.content.strip())
            destination = str(payload.get("destination", "Paris"))
            return {
                "service": str(payload.get("service", service_hint)).strip().lower(),
                "step_description": str(payload.get("step_description", "Book flight")),
                "destination": destination,
                "start_date": str(payload.get("start_date", start_date)),
                "trip_type": str(payload.get("trip_type", trip_type)).strip().lower(),
            }
        except Exception as exc:
            warn_print(f'[PLANNER] "LLM planning unavailable, using fallback plan. ({exc})"')
            return {
                "service": service_hint,
                "step_description": (
                    "Book flight with alternative service"
                    if service_hint == "alternative"
                    else "Book flight"
                ),
                "destination": destination,
                "start_date": start_date,
                "trip_type": trip_type,
            }

    @staticmethod
    def show_plan(plan: Plan) -> None:
        agent_print('[PLANNER] "Plan details:"')
        agent_print(f"[PLANNER] Service: {plan.service_name}")
        for index, step in enumerate(plan.steps, start=1):
            destination = step.params.get("destination", "unknown")
            start_date = step.params.get("start_date", "unknown")
            trip_type = step.params.get("trip_type", "unknown")
            agent_print(
                f"[PLANNER] Step {index}: {step.description} (tool={step.tool}, destination={destination}, start_date={start_date}, trip_type={trip_type})"
            )
