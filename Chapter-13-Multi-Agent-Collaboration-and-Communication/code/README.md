# Chapter 13 Code

This folder will hold the runnable examples and exercise solutions for Chapter 13.

## What is in this folder

- `solutions/README.md`: entry point for the exercise solution guides.
- `solutions/exercise-1-team-selection.md`: conceptual solution notes for team selection.
- `solutions/exercise-2-supervisor-routing.py`: runnable supervisor-routing example.
- `solutions/exercise-3-conflict-handling.py`: runnable conflict-resolution example.
- `solutions/exercise-4-failure-recovery.py`: runnable checkpoint-and-recovery example.

## Prerequisites

- Python available on your machine.
- `uv` installed.

## Install

Run these commands from the Chapter 13 `code/` folder:

```bash
uv sync
```

## Run the solutions

Start with the conceptual Exercise 1 notes, then run the Python solutions.

- Exercise 1: `solutions/exercise-1-team-selection.md`
- Exercise 2: `python solutions/exercise-2-supervisor-routing.py`
- Exercise 3: `python solutions/exercise-3-conflict-handling.py`
- Exercise 4: `python solutions/exercise-4-failure-recovery.py`

## Expected output signals

Use these checks to confirm the solution flow matches the chapter.

- Exercise 1: the reader can explain why each agent belongs on the travel team.
- Exercise 2: the coordinator routes messages based on `type` and `to` fields.
- Exercise 3: conflicting recommendations produce a deterministic resolution.
- Exercise 4: retry output appears before a successful resume from checkpoint.

## Troubleshooting

If a command fails, first confirm you are in the correct folder and that the Python environment is available.
