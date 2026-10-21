from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import (  # noqa: E402
    ApprovalAuthority,
    CancelledError,
    CancellationToken,
    Deadline,
    DeploymentInfo,
    DurableStore,
    Identity,
    RunContext,
    RunState,
    ToolSpec,
    purchase_flight,
)


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

    def run(
        self,
        task: str,
        context: RunContext,
        run_id: str,
    ) -> RunState:
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
                context.approval,
                context.identity,
                spec.name,
                arguments,
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
        return spec.handler(arguments, context)

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


def purchase_handler(
    arguments: dict[str, Any],
    context: RunContext,
) -> str:
    return f"Purchased {arguments['flight_id']} for {context.identity.subject}"


def build_context(authority: ApprovalAuthority) -> RunContext:
    identity = Identity(
        subject="user-1842",
        tenant="travel",
        roles=frozenset({"traveler"}),
    )
    approval = authority.issue(
        identity=identity,
        tool="purchase_flight",
        arguments={"flight_id": "FL-204"},
        idempotency_key="purchase-FL-204-user-1842",
    )
    return RunContext(
        identity=identity,
        deployment=DeploymentInfo(
            agent_version="travel-agent-2026.07.3",
            source_revision="8f23c1d",
            model="qwen2.5:1.5b",
            prompt_version="travel-system-v12",
            policy_version="purchase-policy-v4",
            tool_schema_version="travel-tools-v7",
            evaluation_dataset="travel-critical-v9",
            environment="production",
        ),
        deadline=Deadline.after(30),
        cancellation=CancellationToken(),
        approval=approval,
    )


def build_tools() -> dict[str, ToolSpec]:
    return {
        "purchase_flight": ToolSpec(
            name="purchase_flight",
            schema=purchase_flight,
            handler=purchase_handler,
            requires_approval=True,
            side_effecting=True,
        )
    }


def main() -> None:
    database = Path(__file__).with_name("checkpoint.db")
    database.unlink(missing_ok=True)
    store = DurableStore(database)
    authority = ApprovalAuthority("local-checkpoint-secret")
    context = build_context(authority)
    agent = Agent(authority, build_tools(), store)

    context.cancellation.cancel()
    try:
        agent.execute_tool(
            "purchase_flight",
            {"flight_id": "FL-204"},
            context,
        )
    except CancelledError as error:
        print(f"Cancellation stage: {error}")

    store.close()
    database.unlink(missing_ok=True)


if __name__ == "__main__":
    main()