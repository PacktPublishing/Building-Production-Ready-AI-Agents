from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import (  # noqa: E402
    ApprovalAuthority,
    CancellationToken,
    Deadline,
    DeploymentInfo,
    Identity,
    RunContext,
    ToolSpec,
    purchase_flight,
)


class Agent:
    def __init__(
        self,
        approval_authority: ApprovalAuthority,
    ) -> None:
        self.approval_authority = approval_authority

    def run(self, task: str, context: RunContext) -> str:
        return f"{context.identity.subject}: {task}"

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
    authority = ApprovalAuthority("local-checkpoint-secret")
    context = build_context(authority)
    tools = build_tools()
    agent = Agent(authority)
    agent.authorize_tool(
        tools["purchase_flight"],
        {"flight_id": "FL-204"},
        context,
    )
    print("Authorization stage: approved purchase_flight")


if __name__ == "__main__":
    main()