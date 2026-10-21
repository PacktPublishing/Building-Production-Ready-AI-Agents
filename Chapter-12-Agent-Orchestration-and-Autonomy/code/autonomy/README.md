# Program Autonomy Web App

This mini app simulates an autonomous stock workflow with human approval gates.

You can:

- set a profit goal ("how much you want to make"),
- receive random broker price updates,
- choose which stages run manually vs autonomously,
- approve or reject manual checkpoints,
- inspect a full event log of decisions and outcomes.

## Why this is a strong exercise

It teaches the real control question behind autonomy:

- What can run safely without human review?
- What should pause for manual checks?
- How does changing one policy toggle reshape system behavior?

## Run

1. From this folder, install dependencies:

```bash
uv sync
```

2. Start the app:

```bash
uv run uvicorn app:app --reload --port 8013
```

3. Open:

http://127.0.0.1:8013/

## Suggested mini change

Try this quick experiment:

- turn OFF manual quote checks,
- keep trade approval manual,
- set target profit to 150,
- run 10 cycles,
- compare how often the system pauses.

You should see fewer interruptions, but still keep control before high-impact actions.
