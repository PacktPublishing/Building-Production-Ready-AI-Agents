# Exercise 4 Solution: Inspect an Agent Trajectory

This solution evaluates a real tool-use loop rather than asking a chat model for an answer and inferring what it did. Promptfoo calls a Python provider, the provider gives Ollama a `get_weather` tool, Ollama chooses the tool and its arguments, and Python executes it. OpenTelemetry records that execution so Promptfoo can inspect the path as well as the final response.

## Problem

Run the supplied weather agent evaluation, inspect its trace, and prove that a trajectory assertion catches the wrong expected tool argument even when the final answer remains useful.

## What Is Required

- Confirm that `get_weather` ran with `{"location": "Seattle"}`.
- Confirm that the final response mentions Seattle and the trace contains no error span.
- Change the expected location to `Portland` and verify that `ToolArguments` fails.
- Restore the original expectation after the deliberate failure check.

## Solution files

- [exercise-4-agent.py](./exercise-4-agent.py) implements the Ollama agent and frozen weather tool.
- [exercise-4-promptfooconfig.yaml](./exercise-4-promptfooconfig.yaml) defines the provider, tracing, and assertions.

The weather function returns a frozen fixture rather than live data. This matters because the exercise is testing tool routing and argument extraction. A changing weather API would make those checks harder to reproduce without teaching anything new about agent evaluation.

## How the tool loop works

The provider performs two Ollama calls. On the first call, it sends the user request together with the Python function as a tool definition. Ollama returns a structured tool request such as `get_weather(location="Seattle")` instead of executing Python itself.

The provider then looks up the requested function, executes it with the supplied arguments, and adds the result to the conversation as a `tool` message. The second Ollama call turns that tool result into the final user-facing answer.

During execution, the provider creates a span containing these attributes:

```text
tool.name = get_weather
tool.arguments = {"location": "Seattle"}
```

Promptfoo uses those attributes for `trajectory:tool-used` and `trajectory:tool-args-match`. This is stronger evidence than checking whether the final answer merely mentions a tool name.

## Set up with uv

From the solutions directory, create the environment and install the dependencies declared in `pyproject.toml`:

```powershell
cd Chapter-16-Evaluation/code/solutions
uv sync
```

Install Ollama, download the model, and make sure its server is running:

```powershell
ollama pull qwen3-vl:2b
ollama serve
```

Promptfoo is a Node.js application, so `npx` launches the Promptfoo CLI. The provider configuration sets `pythonExecutable` to `.venv/Scripts/python.exe`, the Windows interpreter created and managed by `uv sync`. This prevents Promptfoo from selecting a different system Python that does not contain the project dependencies.

## Run the eval

In a second terminal, run:

```powershell
cd Chapter-16-Evaluation/code/solutions
npx promptfoo@0.121.19 eval -c exercise-4-promptfooconfig.yaml --no-cache
npx promptfoo@0.121.19 view
```

`--no-cache` ensures the agent executes again and emits a fresh trace. In the results viewer, open the test row and inspect the Trace Timeline. You should see the agent workflow and a `tool get_weather` child span.

The command pins Promptfoo to the version used to validate this chapter. Ollama model tags can change, so record `ollama show qwen3-vl:2b` when you need to reproduce a baseline exactly.

The eval checks four things:

- `ToolRouting`: the agent actually executed `get_weather`.
- `ToolArguments`: the call used exactly `{"location": "Seattle"}`.
- `WorkflowHealth`: no traced operation reported an error.
- `FinalAnswer`: the response mentions Seattle.

A `trajectory:goal-success` assertion is intentionally omitted here. That assertion needs a separate judge provider. Pointing it at `exercise-4-agent.py` would run the weather agent through another complete tool loop, doubling the Ollama calls while asking the system to judge itself.

Try changing `location: Seattle` in the config to `location: Portland` and rerun the eval. The answer may still look useful, but `ToolArguments` should fail because the trace contains the arguments the agent really used.

You should see a response similar to:

```text
✓ Eval complete (ID: eval-5Tw-2026-07-25T16:15:50)

» View results: promptfoo view
» Share with your team: https://promptfoo.app
» Feedback: https://promptfoo.dev/feedback


Results:
  ✓ 1 passed (100%)
  0 failed (0%)
  0 errors (0%)
Duration: 40s (concurrency: 4)
```

## Expected Outcome

You can use the Trace Timeline to prove which tool ran, which arguments it received, and why final-response checks alone are insufficient for agent evaluation.