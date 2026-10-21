# Exercise 2 Solution: Generate an Evaluation Dataset

This exercise asks you to generate a JSON dataset of Promptfoo test cases for a travel booking app.

In this solution, we use the Ollama Python SDK to do exactly that, while enforcing a minimum dataset size and validating output shape.

## Problem

Create at least ten Promptfoo-ready travel-planning cases that cover normal requests, edge cases, and adversarial attempts.

## What Is Required

- Generate at least ten cases in the chapter's `description` and `vars` JSON shape.
- Include normal, edge, and adversarial coverage.
- Describe acceptable behavior instead of prescribing one exact answer.
- Review and validate the generated data before using it in an evaluation.

## Why this matters

When you are starting an evaluation workflow, your first bottleneck is usually test data. If you can generate a structured, repeatable dataset quickly, you can move faster into scoring, thresholds, and CI gates.

For example, a smaller local model may return one well-formed case object even though the request asks for ten. That output is valid JSON, but it is not a valid evaluation dataset. The script therefore constrains the response and validates it instead of trusting JSON parsing alone.

This script gives you a practical starting point:

- Generates at least 10 eval cases.
- Includes normal, edge, and adversarial-style inputs.
- Produces JSON that Promptfoo can load directly.
- Validates the output so broken model formatting fails early.

## Python solution file

Use this script:

- [exercise-2.py](./exercise-2.py)

## Run it

1. Install Ollama and ensure the service is running locally.
2. Pull a model if needed (example: llama3.1).
3. Sync dependencies from the project file.
4. Run the generator.

```bash
cd Chapter-16-Evaluation/code/solutions
uv sync
uv run exercise-2.py --model llama3.1 --min-items 10 --output travel-booking-dataset.json
```

If your Ollama service is remote or non-default, pass host:

```bash
uv run exercise-2.py --model llama3.1 --host http://localhost:11434
```

## Expected output

You should see a message like:

```text
Wrote 10 eval items to travel-booking-dataset.json
```

And the output JSON will follow this structure:

```json
[
  {
    "description": "Seattle business trip stays within budget",
    "vars": {
      "request": "...",
      "expected_response": "..."
    }
  }
]
```

## What just happened

- The script sends a system instruction that forces JSON-only output.
- It labels seed examples as shape guidance and tells the model not to copy them.
- It requests coverage across normal, edge, and adversarial cases.
- It supplies an array JSON schema with the requested item count to Ollama.
- It rejects a top-level object, then validates every Promptfoo field and the minimum number of rows.
- It writes the result to a file you can feed into your eval harness.

## Next step in the chapter flow

You should now have a reviewed dataset that Promptfoo can load without reshaping. Exercise 3 loads this file directly and applies the same assertions to every case.
