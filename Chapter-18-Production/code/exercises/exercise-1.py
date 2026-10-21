from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import ApprovalAuthority, RunContext
from exercise_support import build_context


class Agent:
    def run(self, task: str, context: RunContext) -> str:
        # TODO: Return "<subject>: <task>" using the trusted run context.
        raise NotImplementedError


def main() -> None:
    authority = ApprovalAuthority("local-exercise-secret")
    context = build_context(authority)
    result = Agent().run("Purchase FL-204", context)
    print(f"Context stage: {result}")


if __name__ == "__main__":
    main()
