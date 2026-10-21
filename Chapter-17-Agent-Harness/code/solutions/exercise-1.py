import argparse
from dataclasses import dataclass

from ollama import ChatResponse, chat


MODEL = "qwen2.5:1.5b"


def search_flights(destination: str) -> list[str]:
    """Find available flights to a destination."""
    return [f"FL-204 to {destination} for $450"]


TOOLS = {"search_flights": search_flights}


@dataclass
class RunState:
    messages: list
    step: int = 0
    termination_reason: str | None = None
    final_answer: str | None = None


def can_continue(state: RunState, max_steps: int) -> bool:
    return state.step < max_steps


class AgentHarness:
    def __init__(self, model: str, tools: dict, max_steps: int = 1):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps

    def run(self, task: str) -> RunState:
        state = RunState(
            messages=[
                {
                    "role": "system",
                    "content": "Use the supplied travel tools to complete the task.",
                },
                {"role": "user", "content": task},
            ]
        )

        while can_continue(state, self.max_steps):
            response: ChatResponse = chat(
                model=self.model,
                messages=state.messages,
                tools=list(self.tools.values()),
                think=False,
            )
            state.messages.append(response.message)
            state.step += 1

            if not response.message.tool_calls:
                state.final_answer = response.message.content
                state.termination_reason = "completed"
                return state

            for call in response.message.tool_calls:
                name = call.function.name
                print(f"Tool requested: {name}({call.function.arguments})")
                result = self.tools[name](**call.function.arguments)
                state.messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": str(result),
                    }
                )

        state.termination_reason = "max_steps"
        return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--max-steps", type=int, default=1)
    args = parser.parse_args()

    harness = AgentHarness(args.model, TOOLS, max_steps=args.max_steps)
    result = harness.run(
        "Call search_flights for Paris. Use the tool before answering."
    )

    print(f"Steps: {result.step}")
    print(f"Termination reason: {result.termination_reason}")
