import importlib
import os
from datetime import datetime
from pathlib import Path

import ollama

from console import agent_print, choose_numbered_option, error_print, user_input, user_print, warn_print
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


def _load_solution_module():
    try:
        return importlib.import_module("solution")
    except Exception:
        return None


def _build_primary_service_for_extension(extension_name: str, solution_module):
    if extension_name.startswith("11_") and solution_module and hasattr(solution_module, "ScenarioFlightService"):
        mode_choice = choose_numbered_option(
            "Select test flight scenario:",
            ["always_fail", "fail_once_then_success"],
        )
        selected_mode = "always_fail" if mode_choice == 1 else "fail_once_then_success"
        warn_print(f"[MONITOR] Using test scenario mode: {selected_mode}")
        return solution_module.ScenarioFlightService(mode=selected_mode)

    return PrimaryTravelService()


def _apply_extension_hooks(
    extension_name: str,
    solution_module,
    executor: Executor,
    monitor: Monitor,
    plan,
    trip_type: str,
):
    if solution_module is None:
        return plan

    if hasattr(solution_module, "register_transfer_step") and hasattr(solution_module, "TransferService"):
        solution_module.register_transfer_step(executor, solution_module.TransferService())

    if hasattr(solution_module, "apply_policies_from_json"):
        policy_path = Path(__file__).with_name("policy.json")
        if policy_path.exists():
            solution_module.apply_policies_from_json(executor, str(policy_path))

    if hasattr(solution_module, "apply_contextual_hitl"):
        solution_module.apply_contextual_hitl(executor)

    if hasattr(solution_module, "apply_step_skips"):
        skip_choice = choose_numbered_option(
            "Do you already have a hotel booking?",
            ["No, keep hotel step", "Yes, skip hotel step"],
        )
        plan = solution_module.apply_step_skips(plan, skip_hotel=(skip_choice == 2))

    if extension_name.startswith("04_") and hasattr(solution_module, "BudgetPolicy"):
        budget_raw = user_input("Budget in USD (for example 1200): ").strip()
        budget_usd = int(budget_raw) if budget_raw.isdigit() else 1200
        hotel_nights = 6 if trip_type == "1 week" else 2
        estimated_total = solution_module.estimate_trip_cost(600, hotel_nights, 180)
        ok, reason = solution_module.enforce_budget(solution_module.BudgetPolicy(max_total_usd=budget_usd), estimated_total)
        warn_print(f"[MONITOR] Budget check: {reason}")
        if not ok:
            warn_print("[MONITOR] Budget extension blocked execution before monitor run.")
            return None

    if extension_name.startswith("05_") and hasattr(solution_module, "RetrySpec"):
        retry_choice = choose_numbered_option(
            "Select retry strategy:",
            ["no_retry", "fixed", "exponential_backoff"],
        )
        strategy = ["no_retry", "fixed", "exponential_backoff"][retry_choice - 1]
        attempts_raw = user_input("Retry attempts (for example 2): ").strip()
        attempts = int(attempts_raw) if attempts_raw.isdigit() else 2
        spec = solution_module.RetrySpec(strategy=strategy, attempts=attempts)
        delays = solution_module.get_retry_delays(spec)
        monitor.max_retries = len(delays)
        warn_print(f"[MONITOR] Retry strategy applied: {strategy}, attempts={len(delays)}")

    if extension_name.startswith("07_") and hasattr(solution_module, "choose_failure_action"):
        monitor.failure_actions = {
            "transient_service_outage": solution_module.choose_failure_action(
                "transient_service_outage", "failed to connect"
            ),
            "validation_error": solution_module.choose_failure_action(
                "validation_error", "missing required field"
            ),
            "unknown_failure": solution_module.choose_failure_action(
                "unknown_failure", "unexpected exception"
            ),
        }

    if extension_name.startswith("08_") and hasattr(solution_module, "run_parallel_after_flight"):
        warn_print("[MONITOR] Parallel helper loaded (apply in executor for full async flow).")

    if extension_name.startswith("09_") and hasattr(solution_module, "slice_plan_from_failure"):
        warn_print("[MONITOR] Partial re-execution helper loaded (apply in monitor failure branch).")

    return plan


def run_demo() -> None:
    extension_name = Path(__file__).resolve().parent.name

    ollama_host = os.getenv("PLANNER_OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.getenv("PLANNER_OLLAMA_MODEL", "qwen2.5:1.5b")
    trace_output_dir = os.getenv("PLANNER_TRACE_DIR", "traces")

    metrics = RunMetrics()
    trace = TraceRecorder()
    trace.record("system", "run_started", {"host": ollama_host, "model": ollama_model, "extension": extension_name})

    user_prompt, destination, start_date, trip_type = get_user_trip_request()
    user_print(f'[USER] Prompt: "{user_prompt}"')

    solution_module = _load_solution_module()
    primary_service = _build_primary_service_for_extension(extension_name, solution_module)

    planner = Planner(client=ollama.Client(host=ollama_host), model=ollama_model, trace=trace)
    executor = Executor(
        primary_service=primary_service,
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

    initial_plan = _apply_extension_hooks(
        extension_name,
        solution_module,
        executor,
        monitor,
        initial_plan,
        trip_type,
    )

    if initial_plan is not None:
        monitor.oversee_execution(
            plan=initial_plan,
            planner=planner,
            executor=executor,
        )

    if extension_name.startswith("10_") and solution_module and hasattr(solution_module, "analyze_traces"):
        warn_print("[MONITOR] Running trace analytics extension...")
        solution_module.analyze_traces("traces")

    if extension_name.startswith("12_") and solution_module and hasattr(solution_module, "build_day_blocks"):
        days = 7 if trip_type == "1 week" else 3
        blocks = solution_module.build_day_blocks(start_date, days, destination)
        user_print("[USER] Rich itinerary preview:")
        print(solution_module.format_itinerary(blocks))

    trace.record("system", "run_finished")
    trace_path = trace.save(trace_output_dir)
    agent_print(f'[MONITOR] "Trace saved to: {trace_path}"')


if __name__ == "__main__":
    run_demo()
