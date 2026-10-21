# Exercise 1 Solution: Score LLM Responses

This solution shows how to evaluate two valid LLM responses without relying on strict string matching.

## Problem

Score two travel-planning responses from 1 to 5 for correctness, relevance, completeness, safety, and efficiency. Then justify each score in one sentence.

## What Is Required

- Score both responses against all five metrics.
- Use 1 as poor, 3 as an acceptable baseline, and 5 as excellent.
- Explain why a response can be correct but less relevant or efficient.

## Prompt

```text
Use only the options below to recommend one flight and one hotel for a 5-day Seattle business trip under a $2200 total budget. Show the estimated total and one short rationale.
Flights: Flight A: $450, Flight B: $400.
Hotels: Hotel A: $150/night, Hotel B: $200/night.
```

## What is different between the two responses?

Both responses provide a valid recommendation under budget. The key difference is that Response 2 adds extra content that was not requested.

- Response 1 is tightly focused on the required format.
- Response 2 is still valid, but includes unnecessary additions.

## Scoring rubric (1-5)

- 1: Poor
- 2: Weak
- 3: Acceptable baseline
- 4: Good
- 5: Excellent

Metrics used in this chapter:

- Correctness
- Relevance
- Completeness
- Safety
- Efficiency

## Suggested scores

| Response | Correctness | Relevance | Completeness | Safety | Efficiency | Why |
| --- | --- | --- | --- | --- | --- | --- |
| Response 1 | 5 | 5 | 5 | 5 | 5 | Uses only provided options, computes a valid total, includes rationale, and stays concise. |
| Response 2 | 5 | 4 | 5 | 5 | 4 | Includes every requested element, but adds unrequested content. |

## Short justification by metric

### Correctness

- Response 1: 5, because recommendation and total are mathematically valid under constraints.
- Response 2: 5, for the same reason.

### Relevance

- Response 1: 5, because it follows the exact requested scope.
- Response 2: 4, because it adds content not requested.

### Completeness

- Response 1: 5, because it includes recommendation, total, and rationale.
- Response 2: 5, because it also includes every requested element. Extra content affects relevance and efficiency, not completeness.

### Safety

- Response 1: 5, no unsafe or disallowed content.
- Response 2: 5, no unsafe or disallowed content.

### Efficiency

- Response 1: 5, concise and task-focused.
- Response 2: 4, less efficient due to unnecessary additions.

## Example weighted comparison (optional)

If we use equal weights across all five metrics, the average score is:

- Response 1: (5 + 5 + 5 + 5 + 5) / 5 = 5.0
- Response 2: (5 + 4 + 5 + 5 + 4) / 5 = 4.6

Under this setup, both responses pass, and Response 1 is preferred for strict prompt adherence. Response 2 may still be preferred in user-facing assistants where helpful extras are valued.

## Takeaway

You should now be able to explain why evaluation complements strict equality checks. Two outputs can both be correct, yet differ in relevance, completeness, and efficiency.
