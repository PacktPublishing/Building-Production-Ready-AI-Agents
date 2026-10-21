from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import (
    ActionClaim,
    ApprovalAuthority,
    DurableStore,
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
    ) -> None:
        self.approval_authority = approval_authority
        self.tools = tools
        self.store = store

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
    ) -> Any:
        spec = self.tools.get(name)
        if spec is None:
            raise PermissionError("Tool is not registered")
        self.authorize_tool(spec, arguments, context)
        return self.invoke_tool(spec, arguments, context)

    def invoke_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
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
            owner="worker-1",
        )
        if not claim.execute:
            return claim.result
        result = spec.handler(arguments, context)
        self.store.complete_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            claim.generation,
            result,
        )
        return result

    def reconcile_action(
        self,
        claim: ActionClaim,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
        provider_result: Any | None,
    ) -> Any:
        if context.approval is None:
            raise PermissionError("Side effects require an approval")
        if provider_result is not None:
            self.store.complete_action(
                context.identity.tenant,
                context.identity.subject,
                context.approval.idempotency_key,
                claim.generation,
                provider_result,
            )
            return provider_result
        return self.store.mark_action_retryable(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            claim.generation,
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
        authority = ApprovalAuthority("local-exercise-secret")
        context = build_context(authority)
        agent = Agent(authority, build_tools(), store)
        spec = agent.tools["purchase_flight"]
        arguments = {"flight_id": "FL-204"}

        claim = store.claim_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(spec.name, arguments),
            owner="worker-1",
        )
        assert claim.status == "started"
        print(f"Action status: {claim.status}")

        unknown_claim = store.mark_status_unknown(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            claim.generation,
        )
        assert unknown_claim.status == "status_unknown"
        print(f"Action status: {unknown_claim.status}")

        retryable_claim = agent.reconcile_action(
            unknown_claim,
            spec,
            arguments,
            context,
            None,
        )
        assert retryable_claim.status == "retryable"
        print(f"Action status: {retryable_claim.status}")

        retry_claim = store.claim_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(spec.name, arguments),
            owner="worker-2",
        )
        assert retry_claim.status == "started"
        unknown_claim = store.mark_status_unknown(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            retry_claim.generation,
        )
        agent.reconcile_action(
            unknown_claim,
            spec,
            arguments,
            context,
            "Purchased FL-204 for user-1842",
        )
        completed_claim = store.claim_action(
            context.identity.tenant,
            context.identity.subject,
            context.approval.idempotency_key,
            action_fingerprint(spec.name, arguments),
            owner="worker-3",
        )
        assert completed_claim.status == "completed"
        print(f"Action status: {completed_claim.status}")
        print(f"Reconciled action: {completed_claim.result}")
        store.close()


if __name__ == "__main__":
    main()