from typing import Any

from agent import (
    ApprovalAuthority,
    CancellationToken,
    Deadline,
    DeploymentInfo,
    Identity,
    RunContext,
    ToolSpec,
    purchase_flight,
)


def purchase_handler(arguments: dict[str, Any], context: RunContext) -> str:
    return f"Purchased {arguments['flight_id']} for {context.identity.subject}"


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


def build_context(
    authority: ApprovalAuthority,
    identity: Identity | None = None,
) -> RunContext:
    identity = identity or Identity(
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