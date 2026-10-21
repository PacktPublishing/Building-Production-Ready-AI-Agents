# Exercise 1 Solution: Add and Observe a Step Limit

This solution keeps the Ollama tool-use agent visible while adding its first harness guarantee: a hard limit on model steps.

## Start with an Observable Boundary

Run a real Ollama agent with `search_flights`, stop it after one model step, and inspect why the run ended. This gives you a visible baseline before later exercises add approval and events.

## Build the Smallest Useful State

Begin with the state the loop must return. At this point, it needs only enough information to preserve the conversation and explain why execution stopped:

```python
@dataclass
class RunState:
	messages: list
	step: int = 0
	final_answer: str | None = None
	termination_reason: str | None = None
```

This object does not enforce a limit by itself. It gives `can_continue` a step count to inspect and gives the caller a termination reason to verify. With that purpose visible, the implementation tasks are straightforward:

- Call Ollama with a Python function registered as a tool.
- Store the conversation, step count, final answer, and termination reason in `RunState`.
- Use `can_continue` to enforce `max_steps=1` outside the model.
- Return the state instead of leaving the agent in an open-ended loop.

Next, integrate only that state and boundary into the agent method:

```python
def run(self, task: str) -> RunState:
	state = RunState(messages=[{"role": "user", "content": task}])

	while can_continue(state, self.max_steps):
		response = chat(...)
		state.step += 1
		# Process the response and any requested tools.

	state.termination_reason = "max_steps"
	return state
```

The completed file fills in response handling, but the new harness behavior is already visible: the method returns inspectable state after a deterministic loop condition fails.

## Open the Runnable Version

Now that the state and stopping condition are separate, open [exercise-1.py](./exercise-1.py) to see them integrated around the real Ollama call. Keep the file nearby during the run so you can map the printed step count back to `state.step += 1` and the final reason back to the loop boundary.

## Prepare the Local Run

Install [Ollama](https://ollama.com/), pull the model, and make sure its server is running:

```powershell
ollama pull qwen2.5:1.5b
ollama serve
```

In a second terminal, create the Python environment from the shared project file:

```powershell
cd Chapter-17-Agent-Harness/code/solutions
uv sync
```

## Observe the Stop Reason

```powershell
uv run python exercise-1.py
```

The agent asks Ollama to use `search_flights`. After that model step and tool execution, the harness refuses another model call because the budget is exhausted.

You should see output in this form:

```text
Tool requested: search_flights({'destination': 'Paris'})
Steps: 1
Termination reason: max_steps
```

The exact formatting of tool arguments can vary by Ollama SDK version. The stable result is `Steps: 1` followed by `Termination reason: max_steps`.

## Locate the Runtime Boundary

The important boundary is ordinary Python:

```python
while can_continue(state, self.max_steps):
	response = chat(...)
	state.step += 1
	# Handle the model response and tool calls.

state.termination_reason = "max_steps"
return state
```

The model can request more work, but it cannot change `max_steps` or bypass the loop condition.

## What You Proved

You can now separate three responsibilities in one run:

- Ollama proposes the next action.
- The Python loop counts model turns and decides whether another turn is allowed.
- `RunState` tells the caller that `max_steps`, rather than model choice, ended the run.
