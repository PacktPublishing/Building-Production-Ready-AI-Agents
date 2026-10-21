# Exercise 1: Choose The Travel Team

This exercise is conceptual. It asks you to decide which agents belong in the travel workflow and why.

The point is not to maximize the number of agents. The point is to split the work where the failure modes change, so each role has a clear job.

You do this before writing orchestration logic. Think of it as a design hygiene step that prevents role overlap and unclear handoffs later.

## What This Demos

This exercise demonstrates how to identify the smallest useful team for the Copenhagen travel planner. A good answer usually includes a planner, researcher, policy guard, coordinator, and sometimes a human reviewer.

## Why It Matters

If a role does not change the control flow, the permissions, or the evidence needed for the next step, it probably should not be a separate agent yet.

## Prerequisites

- Read Chapter 13 up through the team design section.
- Be comfortable explaining a workflow in plain language.

## Setup

No code setup is required. This exercise is a reading and reasoning exercise.

## Run

Open the chapter exercise prompt, write your answer in plain language, then compare it with the chapter discussion and the notes in this folder.

The solution is in [solution.md](solution.md).

## Expected Output

Your answer should describe:

- which agents belong on the team,
- what each one is responsible for,
- and why that split is better than using one agent for everything.

If you can explain the team without hand-waving, you have the right idea.