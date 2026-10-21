import argparse
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone

from httpx import TimeoutException
from ollama import ChatResponse, Client, ResponseError


MODEL = "qwen2.5:1.5b"
MODEL_TIMEOUT_SECONDS = 30.0
TOOL_TIMEOUT_SECONDS = 5.0


def search_flights(destination: str) -> list[str]:
    """Find available flights to a destination."""
    return [f"FL-204 to {destination} for $450"]


purchases: list[str] = []


def purchase_flight(flight_id: str) -> str:
    """Purchase a selected flight."""
    purchases.append(flight_id)
    return f"Purchased {flight_id}"


TOOLS = {
    "search_flights": search_flights,
    "purchase_flight": purchase_flight,
}
REQUIRES_APPROVAL = {"purchase_flight"}


@dataclass
class RunState:
    messages: list
    step: int = 0
    events: list[dict] = field(default_factory=list)
    termination_reason: str | None = None
    final_answer: str | None = None


def execute_tool(call, tools: dict, approval: dict | None, completed_actions: dict):
    name = call.function.name
    arguments = dict(call.function.arguments)

    if name not in tools:
        raise ValueError(f"Unknown tool: {name}")
    if name in REQUIRES_APPROVAL:
        if approval is None:
            raise PermissionError(f"Approval required for {name}")
        if approval["tool"] != name or approval["arguments"] != arguments:
            raise PermissionError("Approval does not match the requested action")
        key = approval["idempotency_key"]
        fingerprint = json.dumps(
            {"tool": name, "arguments": arguments},
            sort_keys=True,
            separators=(",", ":"),
        )
        if key in completed_actions:
            stored_fingerprint, stored_result = completed_actions[key]
            if stored_fingerprint != fingerprint:
                raise ValueError(
                    "Idempotency key was already used for a different action"
                )
            return stored_result, True

    result = tools[name](**arguments)
    if name in REQUIRES_APPROVAL:
        completed_actions[key] = (fingerprint, result)
    return result, False


def record_event(state: RunState, event_type: str, **data) -> None:
    state.events.append(
        {
            "type": event_type,
            "step": state.step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
    )


class AgentHarness:
    def __init__(
        self,
        model: str,
        tools: dict,
        approval: dict | None = None,
        model_timeout: float = MODEL_TIMEOUT_SECONDS,
        tool_timeout: float = TOOL_TIMEOUT_SECONDS,
        client=None,
    ):
        self.model = model
        self.tools = tools
        self.approval = approval
        self.tool_timeout = tool_timeout
        self.client = client or Client(timeout=model_timeout)
        self.completed_actions: dict[str, tuple[str, object]] = {}

    def invoke_tool(self, call):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            execute_tool,
            call,
            self.tools,
            self.approval,
            self.completed_actions,
        )
        try:
            return future.result(timeout=self.tool_timeout)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError("Tool execution exceeded its deadline") from None
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def run(self, task: str, max_steps: int = 4) -> RunState:
        state = RunState(
            messages=[
                {
                    "role": "system",
                    "content": "Use the supplied travel tools to complete the task.",
                },
                {"role": "user", "content": task},
            ]
        )
        record_event(state, "run_started")

        while state.step < max_steps:
            record_event(state, "model_requested")
            try:
                response: ChatResponse = self.client.chat(
                    model=self.model,
                    messages=state.messages,
                    tools=list(self.tools.values()),
                    think=False,
                )
            except (ConnectionError, ResponseError, TimeoutException) as error:
                record_event(state, "model_failed", reason=str(error))
                state.termination_reason = "model_timeout" if isinstance(
                    error, TimeoutException
                ) else "model_error"
                record_event(state, "run_stopped", reason=state.termination_reason)
                return state
            state.messages.append(response.message)
            state.step += 1

            if not response.message.tool_calls:
                state.final_answer = response.message.content
                state.termination_reason = "completed"
                record_event(state, "run_completed")
                return state

            for call in response.message.tool_calls:
                name = call.function.name
                record_event(
                    state,
                    "tool_requested",
                    tool=name,
                    arguments=call.function.arguments,
                )

                try:
                    result, replayed = self.invoke_tool(call)
                except PermissionError as error:
                    record_event(
                        state,
                        "policy_denied",
                        tool=name,
                        reason=str(error),
                    )
                    state.termination_reason = "policy_denied"
                    record_event(state, "run_stopped", reason="policy_denied")
                    return state
                except TimeoutError as error:
                    record_event(
                        state,
                        "tool_failed",
                        tool=name,
                        reason=str(error),
                    )
                    state.termination_reason = "tool_timeout"
                    record_event(state, "run_stopped", reason="tool_timeout")
                    return state

                event_type = "tool_replayed" if replayed else "tool_completed"
                record_event(state, event_type, tool=name)
                state.messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": str(result),
                    }
                )

        state.termination_reason = "max_steps"
        record_event(state, "run_stopped", reason="max_steps")
        return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--approved-flight")
    args = parser.parse_args()

    approval = None
    if args.approved_flight:
        approval = {
            "tool": "purchase_flight",
            "arguments": {"flight_id": args.approved_flight},
            "idempotency_key": f"purchase-{args.approved_flight}-user-17",
        }
    harness = AgentHarness(args.model, TOOLS, approval=approval)
    state = harness.run(
        "Call purchase_flight with flight_id FL-204 now. Use the tool."
    )

    for event in state.events:
        detail = event.get("tool") or event.get("reason", "")
        print(f"{event['step']} {event['type']} {detail}")

    print(f"Purchases: {purchases}")
    print(f"Termination reason: {state.termination_reason}")
