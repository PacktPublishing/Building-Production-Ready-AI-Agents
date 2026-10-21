from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import (
    ApprovalAuthority,
    DurableStore,
    Identity,
    RunContext,
    RunState,
    ToolSpec,
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
        return spec.handler(arguments, context)

    def load_or_create_run(
        self,
        run_id: str,
        task: str,
        context: RunContext,
    ) -> RunState:
        # TODO: Return an existing checkpoint only to its original identity.
        # Otherwise create and save a new RunState for this task.
        raise NotImplementedError


def main() -> None:
    with TemporaryDirectory() as directory:
        store = DurableStore(Path(directory) / "exercise.db")
        authority = ApprovalAuthority("local-exercise-secret")
        context = build_context(authority)
        agent = Agent(authority, build_tools(), store)

        run_id = "run-priya-FL-204"
        agent.run("Purchase FL-204", context, run_id)
        restored = agent.run("Purchase FL-204", context, run_id)
        print(f"Checkpoint restored: {restored.run_id}")
        print(f"Owner: {restored.subject}")
        another_identity = Identity(
            "user-9201", "travel", frozenset({"traveler"})
        )
        try:
            agent.run(
                "Purchase FL-204",
                build_context(authority, another_identity),
                run_id,
            )
        except PermissionError as error:
            print(f"Different identity: {error}")
        store.close()


if __name__ == "__main__":
    main()