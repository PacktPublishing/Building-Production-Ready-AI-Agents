import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any
import uuid
from datetime import datetime, timezone


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from agent import (
    ApprovalAuthority,
    DurableStore,
    EventSink,
    JsonLinesEventSink,
    RunContext,
    RunState,
    ToolSpec,
    action_fingerprint,
)
from exercise_support import build_context, build_tools


class Agent:
    def __init__(
        self,
        approval_authority: ApprovalAuthority,
        tools: dict[str, ToolSpec],
        store: DurableStore,
        event_sink: EventSink,
    ) -> None:
        self.approval_authority = approval_authority
        self.tools = tools
        self.store = store
        self.event_sink = event_sink

    def emit_action_event(
        self,
        event_type: str,
        spec: ToolSpec,
        context: RunContext,
    ) -> None:
        if context.approval is None:
            raise PermissionError("Side effects require an approval")
        event = {
            "event_id": f"event-{uuid.uuid4().hex}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant": context.identity.tenant,
            "subject": context.identity.subject,
            "tool_name": spec.name,
            "idempotency_key": context.approval.idempotency_key,
        }
        run_id = f"action-events-{context.approval.idempotency_key}"
        state = self.store.load_checkpoint(run_id) or RunState(
            run_id=run_id,
            messages=[],
            subject=context.identity.subject,
            tenant=context.identity.tenant,
        )
        state.events.append(event)
        self.store.save_event_checkpoint(state, event)
        self.publish_pending_events()

    def publish_pending_events(self) -> None:
        for event in self.store.load_pending_events():
            try:
                self.event_sink.emit(event)
            except Exception:
                return
            self.store.mark_event_published(event["event_id"])

    def run(self, task: str, context: RunContext, run_id: str) -> RunState:
        context.cancellation.raise_if_cancelled()
        context.deadline.remaining_seconds()
        return self.load_or_create_run(run_id, task, context)

    def authorize_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> None:
        if spec.auth_policy.logged_in and not context.identity.subject:
            raise PermissionError("Tool requires a signed-in user")
        if not context.identity.roles.intersection(spec.allowed_roles):
            raise PermissionError("Identity is not allowed to use this tool")
        if spec.requires_approval:
            self.approval_authority.verify(
                context.approval, context.identity, spec.name, arguments
            )

    def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: RunContext,
        owner: str = "worker-1",
    ) -> Any:
        self.publish_pending_events()
        spec = self.tools.get(name)
        if spec is None:
            raise PermissionError("Tool is not registered")
        self.authorize_tool(spec, arguments, context)
        return self.invoke_tool(spec, arguments, context, owner)

    def invoke_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
        owner: str = "worker-1",
    ) -> Any:
        context.cancellation.raise_if_cancelled()
        context.deadline.remaining_seconds()
        if not spec.side_effecting:
            return spec.handler(arguments, context)
        if context.approval is None:
            raise PermissionError("Side effects require an approval")

        claim = self.store.claim_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(spec.name, arguments),
            owner=owner,
        )
        if not claim.execute:
            self.emit_action_event("action_replayed", spec, context)
            return claim.result
        result = spec.handler(arguments, context)
        self.store.complete_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            claim.generation,
            result,
        )
        self.emit_action_event("action_completed", spec, context)
        return result

    def reconcile_action(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
        provider_result: Any,
    ) -> None:
        if context.approval is None:
            raise PermissionError("Side effects require an approval")
        self.store.reconcile_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(spec.name, arguments),
            provider_result=provider_result,
            committed=True,
        )

    def load_or_create_run(
        self,
        run_id: str,
        task: str,
        context: RunContext,
    ) -> RunState:
        state = self.store.load_checkpoint(run_id)
        if state is not None:
            if (
                state.subject != context.identity.subject
                or state.tenant != context.identity.tenant
            ):
                raise PermissionError("Run belongs to another identity")
            return state
        state = RunState(
            run_id=run_id,
            messages=[{"role": "user", "content": task}],
            subject=context.identity.subject,
            tenant=context.identity.tenant,
        )
        self.store.save_checkpoint(state)
        return state


def main() -> None:
    with TemporaryDirectory() as directory:
        store = DurableStore(Path(directory) / "exercise.db")
        events_path = Path(directory) / "events.jsonl"
        authority = ApprovalAuthority("local-exercise-secret")
        context = build_context(authority)
        agent = Agent(
            authority,
            build_tools(),
            store,
            JsonLinesEventSink(events_path),
        )
        arguments = {"flight_id": "FL-204"}

        first = agent.execute_tool(
            "purchase_flight", arguments, context, owner="worker-1"
        )
        replay = agent.execute_tool(
            "purchase_flight", arguments, context, owner="worker-2"
        )
        print(f"First worker: {first}")
        print(f"Second worker replay: {replay}")
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        print(f"Events: {', '.join(event['event_type'] for event in events)}")
        store.close()


if __name__ == "__main__":
    main()