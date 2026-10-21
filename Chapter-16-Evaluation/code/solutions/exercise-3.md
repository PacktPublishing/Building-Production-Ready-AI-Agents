# Exercise 3 Solution: Run and Inspect an Evaluation

This solution completes the workflow started in Exercise 2. Promptfoo loads the travel dataset directly, sends every `request` to the target model, and grades each response against that case's `expected_response`.

## Problem

Run the generated dataset through Promptfoo, inspect the named metrics, add a no-valid-combination edge case, and confirm that the new case is evaluated.

## What Is Required

- Run the travel dataset with the supplied Promptfoo configuration.
- Inspect `Safety` and `InstructionFollowing` for every case.
- Add one case where every flight-and-hotel combination exceeds the budget.
- Confirm that the model explains the constraint instead of inventing an option or discount.

## Why this matters

An evaluation dataset becomes useful when the harness can run every case consistently. Keeping the cases in a separate JSON file lets you add scenarios without duplicating the prompt, provider, or assertions.

## Configuration file

The runnable configuration is here:

- [exercise-3-promptfooconfig.yaml](./exercise-3-promptfooconfig.yaml)
- [travel-booking-dataset.json](./travel-booking-dataset.json)

The configuration uses two local models through Ollama:

- `qwen3-vl:2b` produces the travel recommendation.
- `llama3.1` acts as an independent rubric grader.

The `defaultTest` block applies the same assertions to every case loaded from `travel-booking-dataset.json`. The deterministic assertion rejects a false booking confirmation, while the rubric compares the response with the expected behavior for that case.

## Run the eval

Install [Ollama](https://ollama.com/), download both models, and make sure Ollama is running:

```powershell
ollama pull qwen3-vl:2b
ollama pull llama3.1
ollama serve
```

In a second terminal, change to the solutions directory and run Promptfoo:

```powershell
cd Chapter-16-Evaluation/code/solutions
npx promptfoo@0.121.19 eval -c exercise-3-promptfooconfig.yaml
npx promptfoo@0.121.19 view
```

The `eval` command uses the Exercise 3 configuration in the current directory. The `view` command then opens the local results viewer. Add options such as `--output results.json` only when you need a separate machine-readable result file.

No API key is required. Promptfoo connects to Ollama at `http://localhost:11434` by default. The eval passes only when every required assertion passes.

The exact pass count depends on the model versions and your generated dataset. A completed run reports a summary in this form:

```text
Results:
  ✓ <passed> passed
  <failed> failed
  0 errors (0%)
```

## Inspect the results

In the Promptfoo results viewer, inspect the generated response and the named metrics:

- `Safety`
- `InstructionFollowing`

If an assertion fails, Promptfoo shows which requirement was missed. For example, a model that invents a discount should fail the case whose expected behavior explicitly forbids that discount.

## Add the edge case

Add one more object to `travel-booking-dataset.json` for a trip where no combination fits the budget. State the expected behavior as explaining that no valid combination exists rather than inventing an option. Rerun the eval and confirm that Promptfoo reports 11 cases.

## Reproducibility note

The command pins Promptfoo to `0.121.19`. Ollama model tags can still change over time, so record the output of `ollama show qwen3-vl:2b` and `ollama show llama3.1` when you need to reproduce a baseline exactly.

## Expected Outcome

You can identify which assertion failed, connect that failure to a specific requirement, and verify that the expanded dataset is part of the run.
