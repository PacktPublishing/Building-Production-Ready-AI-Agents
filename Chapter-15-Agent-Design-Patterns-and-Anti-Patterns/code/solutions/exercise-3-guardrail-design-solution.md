# Exercise 3 Solution: Guardrail Design

## Problem
Design two guardrails for the Copenhagen workflow and tie each to a known anti-pattern risk.

## What is required

- Add two guardrails that address two different anti-pattern risks.
- Explain how each guardrail applies to the Copenhagen booking story.

## How this solution was created

We used a three-step method:

1. Start from anti-pattern risks identified earlier.
2. Select guardrails that directly block those risks in runtime behavior.
3. Tie each guardrail to a concrete moment in the travel-booking flow.

### How to answer with this method

Use this response pattern:

- Guardrail name.
- Anti-pattern addressed.
- Design details (what is enforced).
- How it connects to the Copenhagen workflow.

## Solution

**Guardrail A: Deterministic routing and tool eligibility validation**

In plain terms, this guardrail stops the agent from calling tools in a random order. We force a clear sequence: retrieve options first, analyze next, run policy checks, and only then execute actions. Before a tool runs, we validate the input. After a tool returns, we validate the result before moving forward. If a booking step appears before policy context is ready, the step is blocked and sent to policy handling first.

In the Copenhagen story, this means the agent does not jump straight to booking. It first gathers flight and hotel options, then checks policy and budget constraints, and only then continues. The same request shape gets the same flow, which makes behavior easier to trust.

**Guardrail B: Tiered action confirmation**

In plain terms, this guardrail decides when the agent can act alone and when a human must approve. Read-only work is automatic. Low-risk write actions go through rule checks. High-risk actions must pause for human confirmation. If confirmation is missing, execution stops.

In the Copenhagen story, the agent can search flights and hotels on its own, but it cannot finalize a booking above the 1800 USD approval threshold without a person signing off. This gives speed in research and control at the moment of real risk.

## Why this works
Both guardrails are enforceable at runtime rather than aspirational recommendations. Each one directly maps to a known failure class, and each one is grounded in the Copenhagen use case so the design stays practical instead of abstract.

