from pathlib import Path
import sys
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import ApprovalAuthority, RunContext, ToolSpec
from exercise_support import build_context, build_tools


class Agent:
    def __init__(self, approval_authority: ApprovalAuthority) -> None:
        self.approval_authority = approval_authority

    def run(self, task: str, context: RunContext) -> str:
        return f"{context.identity.subject}: {task}"

    def authorize_tool(
        self,
        spec: ToolSpec,
        arguments: dict[str, Any],
        context: RunContext,
    ) -> None:
        # TODO: Enforce the decorated tool's login and role policy. If
        # approval is required, verify this identity, tool, and arguments.
        raise NotImplementedError


def main() -> None:
    authority = ApprovalAuthority("local-exercise-secret")
    context = build_context(authority)
    agent = Agent(authority)
    agent.authorize_tool(
        build_tools()["purchase_flight"],
        {"flight_id": "FL-204"},
        context,
    )
    print("Authorization stage: approved purchase_flight")


if __name__ == "__main__":
    main()