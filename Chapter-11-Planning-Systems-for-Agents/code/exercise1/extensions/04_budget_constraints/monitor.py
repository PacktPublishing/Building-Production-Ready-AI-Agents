from datetime import datetime, timedelta
from typing import Dict, Optional

from console import agent_print, choose_numbered_option, error_print, user_print, warn_print
from executor import Executor
from models import Plan, RunMetrics, StepResult
from planner import Planner
from tracing import TraceRecorder


class Monitor:
    def __init__(self, metrics: RunMetrics, trace: TraceRecorder, max_retries: int = 1) -> None:
        self.metrics = metrics
        self.trace = trace
        self.max_retries = max_retries
        self.failure_actions: Dict[str, str] = {
            "transient_service_outage": "retry_then_fallback",
            "validation_error": "fallback_only",
            "unknown_failure": "fallback_only",
        }

    def oversee_execution(
        self,
        plan: Plan,
        planner: Planner,
        executor: Executor,
    ) -> None:
        self.trace.record("monitor", "oversee_execution_start", {"service": plan.service_name})
        results = executor.execute_plan(plan)
        if self._all_successful(results):
            agent_print('[MONITOR] "Plan executed successfully!"')
            self._print_itinerary(plan, results)
            self._print_run_summary("success", "initial plan")
            return

        failed_step = self._first_failed_step(results)
        if failed_step is None:
            error_print('[MONITOR] "Plan failed for unknown reasons."')
            self._print_run_summary("failed", "unknown failure")
            return

        error_print(f'[MONITOR] "Detected failure in step: {failed_step.description}."')
        failure_category = self._classify_failure(failed_step)
        warn_print(f'[MONITOR] "Failure category: {failure_category}."')
        action = self.failure_actions.get(failure_category, "fallback_only")
        warn_print(f'[MONITOR] "Policy action: {action}."')
        self.trace.record(
            "monitor",
            "failure_detected",
            {
                "step": failed_step.description,
                "tool": failed_step.tool,
                "category": failure_category,
                "action": action,
            },
        )

        retry_results: list[StepResult] = []
        step_policy = executor.get_step_policy(failed_step.tool)
        retry_budget = step_policy.max_retries or self.max_retries
        if action == "retry_then_fallback" and retry_budget > 0:
            warn_print('[MONITOR] "Applying retry strategy for flight booking..."')
            for attempt in range(1, retry_budget + 1):
                self.metrics.retry_count += 1
                self.trace.record("monitor", "retry_attempt", {"attempt": attempt})
                retry_results = executor.execute_plan(plan, is_retry=True)
                if self._all_successful(retry_results):
                    agent_print('[MONITOR] "Plan executed successfully after retry."')
                    self._print_itinerary(plan, retry_results)
                    self._print_run_summary("success", "retry")
                    return
        else:
            warn_print('[MONITOR] "Retry skipped by policy for this failure category/step."')

        warn_print('[MONITOR] "Retry failed. Applying fallback policy."')
        warn_print('[MONITOR] "Switching airline/provider changes itinerary details and needs your approval."')

        self.metrics.approval_prompts += 1
        approval_choice = choose_numbered_option(
            "Approve switching to an alternative airline/service?",
            ["Approve switch", "Decline switch"],
        )
        if approval_choice != 1:
            warn_print('[MONITOR] "User declined provider switch. Stopping execution without booking."')
            user_print('[USER] No booking was made. You can change constraints or try again later.')
            self.trace.record("monitor", "approval_declined")
            self._print_run_summary("cancelled", "user declined provider switch")
            return

        self.metrics.approval_granted += 1
        self.metrics.replan_count += 1
        warn_print('[MONITOR] "User approved switch. Proceeding with alternative booking service."')
        self.trace.record("monitor", "approval_granted")

        feedback = "Primary flight booking service unavailable after retry"
        new_plan = planner.replan_for_service_failure(feedback)
        new_results = executor.execute_plan(new_plan)
        if self._all_successful(new_results):
            self._report_user_visible_changes(plan, new_plan, new_results)
            agent_print(
                '[MONITOR] "Plan executed successfully after replanning with '
                'alternative service."'
            )
            self._print_itinerary(new_plan, new_results)
            self._print_run_summary("success", "replan")
        else:
            error_print('[MONITOR] "Replanned execution failed. Escalating again."')
            self._print_run_summary("failed", "replan failed")

    @staticmethod
    def _report_user_visible_changes(
        original_plan: Plan,
        new_plan: Plan,
        new_results: list[StepResult],
    ) -> None:
        if original_plan.service_name != new_plan.service_name:
            warn_print(
                '[MONITOR] "User-visible update: switched airline provider due to reliability policy."'
            )

        if not new_results:
            return

        details = new_results[0].details or {}
        provider = details.get("provider")
        routing = details.get("routing")
        stopovers = details.get("stopovers")

        if provider:
            warn_print(f'[MONITOR] "Provider: {provider}"')
        if routing:
            warn_print(f'[MONITOR] "Routing update: {routing}"')
        if stopovers is not None:
            warn_print(f'[MONITOR] "Stopovers: {stopovers}"')

    @staticmethod
    def _print_itinerary(plan: Plan, results: list[StepResult]) -> None:
        if not plan.steps:
            return

        step = plan.steps[0]
        destination = step.params.get("destination", "Unknown")
        start_date = step.params.get("start_date", "Unknown")
        trip_type = step.params.get("trip_type", "Unknown")

        duration_days = 7 if trip_type == "1 week" else 3
        end_date = "Unknown"
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
            parsed_end = parsed_start + timedelta(days=duration_days - 1)
            end_date = parsed_end.strftime("%Y-%m-%d")
        except ValueError:
            end_date = "Could not compute (invalid date format)"

        details = results[0].details if results else None
        provider = details.get("provider") if details else None
        routing = details.get("routing") if details else None
        stopovers = details.get("stopovers") if details else None

        agent_print('[MONITOR] "Final itinerary:"')
        agent_print(f"[MONITOR] Destination: {destination}")
        agent_print(f"[MONITOR] Start date: {start_date}")
        agent_print(f"[MONITOR] Trip type: {trip_type}")
        agent_print(f"[MONITOR] End date: {end_date}")
        if provider:
            agent_print(f"[MONITOR] Airline/provider: {provider}")
        if routing:
            agent_print(f"[MONITOR] Routing: {routing}")
        if stopovers is not None:
            agent_print(f"[MONITOR] Stopovers: {stopovers}")

    @staticmethod
    def _all_successful(results: list[StepResult]) -> bool:
        return all(result.success for result in results)

    @staticmethod
    def _classify_failure(result: StepResult) -> str:
        message = result.message.lower()
        if "failed to connect" in message or "timeout" in message:
            return "transient_service_outage"
        if "invalid" in message or "missing" in message:
            return "validation_error"
        return "unknown_failure"

    @staticmethod
    def _first_failed_step(results: list[StepResult]) -> Optional[StepResult]:
        for result in results:
            if not result.success:
                return result
        return None

    def _print_run_summary(self, status: str, resolution: str) -> None:
        step_success_rate = self.metrics.success_rate()
        mission_success_rate = 100.0 if status == "success" else 0.0
        agent_print('[MONITOR] "Run summary:"')
        agent_print(f"[MONITOR] Status: {status}")
        agent_print(f"[MONITOR] Resolution: {resolution}")
        agent_print(f"[MONITOR] Steps attempted: {self.metrics.steps_attempted}")
        agent_print(f"[MONITOR] Steps succeeded: {self.metrics.steps_succeeded}")
        agent_print(f"[MONITOR] Steps failed: {self.metrics.steps_failed}")
        agent_print(f"[MONITOR] Retries: {self.metrics.retry_count}")
        agent_print(f"[MONITOR] Replans: {self.metrics.replan_count}")
        agent_print(
            f"[MONITOR] Approval prompts/granted: {self.metrics.approval_prompts}/{self.metrics.approval_granted}"
        )
        agent_print(f"[MONITOR] Mission success rate: {mission_success_rate:.1f}%")
        agent_print(f"[MONITOR] Step efficiency rate: {step_success_rate:.1f}%")
        self.trace.record(
            "monitor",
            "run_summary",
            {
                "status": status,
                "resolution": resolution,
                "steps_attempted": self.metrics.steps_attempted,
                "steps_succeeded": self.metrics.steps_succeeded,
                "steps_failed": self.metrics.steps_failed,
                "retry_count": self.metrics.retry_count,
                "replan_count": self.metrics.replan_count,
                "approval_prompts": self.metrics.approval_prompts,
                "approval_granted": self.metrics.approval_granted,
                "mission_success_rate": round(mission_success_rate, 1),
                "step_success_rate": round(step_success_rate, 1),
            },
        )
