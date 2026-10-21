from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import (  # noqa: E402
    ApprovalAuthority,
    CancellationToken,
    Deadline,
    DeploymentInfo,
    Identity,
    RunContext,
)


class Agent:
    def run(self, task: str, context: RunContext) -> str:
        return f"{context.identity.subject}: {task}"


def build_context() -> RunContext:
    return RunContext(
        identity=Identity(
            subject="user-1842",
            tenant="travel",
            roles=frozenset({"traveler"}),
        ),
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
    )


def main() -> None:
    agent = Agent()
    result = agent.run("Purchase FL-204", build_context())
    print(f"Context stage: {result}")


if __name__ == "__main__":
    main()