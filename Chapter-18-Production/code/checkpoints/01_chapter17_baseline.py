from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Any


MAX_STEPS = 4
MODEL_TIMEOUT_SECONDS = 30.0
TOOL_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Approval:
    tool: str
    arguments: dict[str, Any]
    idempotency_key: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class RunState:
    messages: list[dict[str, Any]]
    step: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str | None = None
    termination_reason: str | None = None


class FixedModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = responses.copy()

    def chat(
        self,
        messages: list[dict[str, Any]],
        timeout: float,
    ) -> ModelResponse:
        if timeout <= 0:
            raise TimeoutError("Model deadline exceeded")
        return self.responses.pop(0)


class Chapter17Harness:
    """The complete runtime contract carried into Chapter 18."""

    def __init__(self, model: FixedModel, max_steps: int = MAX_STEPS) -> None:
        self.model = model
        self.max_steps = max_steps
        self.purchases: list[str] = []
        self.completed_actions: dict[str, tuple[ToolCall, str]] = {}

    def record_event(self, state: RunState, event_type: str, **data: Any) -> None:
        state.events.append({"event_type": event_type, "step": state.step, **data})

    def execute_tool(
        self,
        call: ToolCall,
        approval: Approval | None,
    ) -> tuple[str, bool]:
        if call.name != "purchase_flight":
            raise ValueError(f"Unknown tool: {call.name}")
        if approval is None:
            raise PermissionError("Purchase approval required")
        if approval.tool != call.name or approval.arguments != call.arguments:
            raise PermissionError("Approval does not match requested action")
        if approval.idempotency_key in self.completed_actions:
            stored_call, stored_result = self.completed_actions[
                approval.idempotency_key
            ]
            if stored_call != call:
                raise ValueError("Idempotency key belongs to another action")
            return stored_result, True

        flight_id = str(call.arguments["flight_id"])
        self.purchases.append(flight_id)
        result = f"Purchased {flight_id}"
        self.completed_actions[approval.idempotency_key] = (call, result)
        return result, False

    def invoke_tool(
        self,
        call: ToolCall,
        approval: Approval | None,
    ) -> tuple[str, bool]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.execute_tool, call, approval)
        try:
            return future.result(timeout=TOOL_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError("Tool deadline exceeded") from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def stop(self, state: RunState, reason: str) -> RunState:
        state.termination_reason = reason
        self.record_event(state, "run_stopped", reason=reason)
        return state

    def run(self, task: str, approval: Approval | None = None) -> RunState:
        state = RunState(messages=[{"role": "user", "content": task}])
        self.record_event(state, "run_started")

        while state.step < self.max_steps:
            self.record_event(state, "model_requested")
            try:
                response = self.model.chat(
                    state.messages,
                    timeout=MODEL_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                return self.stop(state, "model_timeout")
            state.step += 1

            if not response.tool_calls:
                state.final_answer = response.content
                state.termination_reason = "completed"
                self.record_event(state, "run_completed")
                return state

            for call in response.tool_calls:
                self.record_event(state, "tool_requested", tool=call.name)
                try:
                    result, replayed = self.invoke_tool(call, approval)
                except PermissionError:
                    self.record_event(state, "policy_denied", tool=call.name)
                    return self.stop(state, "policy_denied")
                except TimeoutError:
                    return self.stop(state, "tool_timeout")
                self.record_event(
                    state,
                    "tool_completed",
                    tool=call.name,
                    replayed=replayed,
                )
                state.messages.append({"role": "tool", "content": result})

        return self.stop(state, "max_steps")


def main() -> None:
    purchase = ToolCall("purchase_flight", {"flight_id": "FL-204"})
    model = FixedModel(
        [
            ModelResponse(tool_calls=[purchase]),
            ModelResponse(tool_calls=[purchase]),
            ModelResponse(content="Purchased FL-204"),
        ]
    )
    approval = Approval(
        tool="purchase_flight",
        arguments={"flight_id": "FL-204"},
        idempotency_key="purchase-FL-204-user-17",
    )
    harness = Chapter17Harness(model)
    state = harness.run("Purchase FL-204", approval)

    print(f"Termination reason: {state.termination_reason}")
    print(f"Purchases: {harness.purchases}")
    print("Events:", [event["event_type"] for event in state.events])


if __name__ == "__main__":
    main()
