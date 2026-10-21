# Exercise 1 Solution: Pattern Selection

## Problem
Book a policy-compliant trip to Copenhagen (Aug 12-15), keep total spend under 2200 USD, prefer morning flights, and require explicit approval above 1800 USD.

## What is required

- Classify the workflow using the pattern selection matrix.
- Pick one pattern as the better fit and justify it in 5-7 sentences.
- Name one plausible but worse-fit pattern and explain why.

## How this solution was created

We used a simple three-step method:

1. Describe the workflow shape and constraints.
2. Choose the pattern that best matches control, cost, and governance needs.
3. Contrast it against a plausible but weaker alternative.

**How to answer with this method**

Use this response pattern:

- Task classification.
- Pattern chosen.
- Why this pattern fits the task shape and constraints.
- Pattern that would be worse.
- Why it is worse here.

## Solution

**Task classification**
- Workflow shape: multi-step decomposition with clear subtasks.
- Subtasks: flight retrieval, hotel retrieval, policy check, and final synthesis.
- Governance needs: explicit approval gate when total exceeds 1800 USD.

**Pattern chosen**
- Planner + workers (bounded loop).

**Why this pattern**
This request decomposes naturally into independent subtasks that can run in parallel, especially flight and hotel search. A planner can sequence and coordinate those subtasks while workers execute focused tool calls with fewer prompt ambiguities. Because cost and policy are explicit constraints, the planner can insert a deterministic policy check before any side-effecting action. The bounded loop gives controlled autonomy, which prevents runaway iteration when options are sparse or conflicting. This pattern also improves observability because each worker step is traceable and attributable to a specific planning decision. Compared with a single generalist agent, planner + workers reduces hidden reasoning and makes failures easier to isolate. With a max-iteration cap and stop conditions, the architecture stays within predictable latency and spend limits.

**Pattern that would be worse**
- Open-ended peer-to-peer negotiation.

**Why it is worse here**
This task does not require unconstrained negotiation among equal agents; it requires deterministic convergence under budget and policy constraints. Peer-to-peer adds coordination overhead, weakens centralized policy enforcement, and increases non-determinism without improving outcome quality for this problem shape.

