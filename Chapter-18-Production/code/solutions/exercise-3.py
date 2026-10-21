from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import ApprovalAuthority, RunContext, ToolSpec
from exercise_support import build_context, build_tools


class Agent:
    def __init__(
        self,
        approval_authority: ApprovalAuthority,
        tools: dict[str, ToolSpec] | None = None,
    ) -> None:
        self.approval_authority = approval_authority
        self.tools = tools or {}

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
        return spec.handler(arguments, context)


def main() -> None:
    authority = ApprovalAuthority("local-exercise-secret")
    context = build_context(authority)
    agent = Agent(authority, build_tools())
    result = agent.execute_tool(
        "purchase_flight",
        {"flight_id": "FL-204"},
        context,
    )
    print(f"Isolation stage: {result}")
    try:
        agent.execute_tool("delete_account", {}, context)
    except PermissionError as error:
        print(f"Unknown tool: {error}")


if __name__ == "__main__":
    main()
