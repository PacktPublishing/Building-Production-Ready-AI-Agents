import os
from datetime import datetime

import ollama

from console import agent_print, choose_numbered_option, error_print, user_input, user_print
from executor import Executor
from models import RunMetrics
from monitor import Monitor
from planner import Planner
from services import (
    AlternativeTravelService,
    HotelService,
    ItineraryService,
    PrimaryTravelService,
)
from tracing import TraceRecorder


def get_user_trip_request() -> tuple[str, str, str, str]:
    agent_print("[PLANNER] Trip Planner: I can help plan your trip, but I need a destination first.")

    destination = ""
    while not destination:
        destination = user_input("Destination: ").strip()
        if not destination:
            error_print("[PLANNER] Destination is required (for example: Paris, Tokyo, Nairobi).")

    start_date = ""
    while not start_date:
        proposed_date = user_input("Start date (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(proposed_date, "%Y-%m-%d")
            start_date = proposed_date
        except ValueError:
            error_print("[PLANNER] Invalid date format. Please use YYYY-MM-DD.")

    trip_type_options = ["Weekend (3 days)", "1 week (7 days)"]
    trip_type_choice = choose_numbered_option("Choose trip type:", trip_type_options)
    trip_type = "weekend" if trip_type_choice == 1 else "1 week"

    extra_details = user_input("Any preferences or constraints? (optional): ").strip()
    if extra_details:
        prompt = (
            f"Plan a {trip_type} trip to {destination} starting {start_date}. "
            f"Preferences: {extra_details}"
        )
    else:
        prompt = f"Plan a {trip_type} trip to {destination} starting {start_date} for me."

    return prompt, destination, start_date, trip_type


def run_demo() -> None:
    ollama_host = os.getenv("PLANNER_OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("PLANNER_OLLAMA_MODEL", "qwen2.5:1.5b")
    trace_output_dir = os.getenv("PLANNER_TRACE_DIR", "traces")

    metrics = RunMetrics()
    trace = TraceRecorder()
    trace.record("system", "run_started", {"host": ollama_host, "model": ollama_model})

    user_prompt, destination, start_date, trip_type = get_user_trip_request()
    user_print(f'[USER] Prompt: "{user_prompt}"')
    trace.record(
        "user",
        "trip_request",
        {
            "destination": destination,
            "start_date": start_date,
            "trip_type": trip_type,
        },
    )

    planner = Planner(client=ollama.Client(host=ollama_host), model=ollama_model, trace=trace)
    executor = Executor(
        primary_service=PrimaryTravelService(),
        alternative_service=AlternativeTravelService(),
        hotel_service=HotelService(),
        itinerary_service=ItineraryService(),
        metrics=metrics,
        trace=trace,
    )
    monitor = Monitor(metrics=metrics, trace=trace, max_retries=1)

    initial_plan = planner.generate_plan(
        user_prompt,
        destination=destination,
        start_date=start_date,
        trip_type=trip_type,
    )

    monitor.oversee_execution(
        plan=initial_plan,
        planner=planner,
        executor=executor,
    )

    trace.record("system", "run_finished")
    trace_path = trace.save(trace_output_dir)
    agent_print(f'[MONITOR] "Trace saved to: {trace_path}"')


if __name__ == "__main__":
    run_demo()
