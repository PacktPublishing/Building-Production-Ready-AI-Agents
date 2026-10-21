# Exercise 1 Solution: Choose The Travel Team

This exercise is intentionally conceptual. Before the reader writes code, the most important job is to decide which agents belong in the travel workflow and why.

## A good solution

For the Copenhagen travel planner, a small team is usually enough:

- Planner: turns the request into a structured travel plan.
- Researcher: gathers flights, hotels, and timing options.
- Policy Guard: checks budget and approval rules.
- Coordinator: keeps the handoff trace visible and decides the next step.
- Human Reviewer: steps in when approval or clarification is required.

## Why this shape works

The goal is not to maximize the number of agents. The goal is to split the work at the point where the failure modes change.

- The planner handles intent.
- The researcher handles facts.
- The policy guard handles permission.
- The coordinator handles routing.
- The human reviewer handles typed approval when automation should pause.

## What the reader should notice

If a role does not change the control flow, the permissions, or the evidence needed for the next step, it probably should not be a separate agent yet.