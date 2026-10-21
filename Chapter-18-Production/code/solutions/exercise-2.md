# Exercise 2 Solution: Guard Priya's Purchase

This solution keeps `Agent.run` from Exercise 1 and adds `authorize_tool`. Priya's exact approved purchase of `FL-204` may pass only when both her role and approval match.

## Add the Authorization Method

The [starter](../exercises/exercise-2.py) asks you to complete two checks inside the `Agent`:

- The caller must satisfy the login and roles declared by the tool's `@auth` decorator.
- A tool that requires approval must pass exact-action verification.

`ToolSpec` exposes the decorator metadata as `auth_policy` and `allowed_roles`. This separates approval from general authorization. Priya may have the `traveler` role, but her approval still names one identity and one exact action.

## Open the Runnable Version

Open [exercise-2.py](./exercise-2.py) to compare the class with Exercise 1 and find the new `authorize_tool` method.

## Prepare the Local Run

This exercise requires Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/). Prepare the Chapter 18 environment:

```powershell
cd Chapter-18-Production/code
uv sync
```

This deterministic exercise does not require Ollama.

## Test the Approval Boundary

```powershell
uv run python solutions/exercise-2.py
```

Expected output:

```text
Authorization stage: approved purchase_flight
```

## What You Proved

A valid signature is not a reusable permission slip. Verification also binds the approval to Priya's trusted identity and the exact `purchase_flight` arguments she confirmed.
