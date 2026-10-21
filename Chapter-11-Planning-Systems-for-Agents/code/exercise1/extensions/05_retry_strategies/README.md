# 05 Retry Strategies

## Before -> After

Before: all retries behaved the same way.

After: each tool can use a strategy (`no_retry`, `fixed`, `exponential_backoff`).

## User Benefit

The agent recovers faster and more intelligently from outages, reducing failed runs and wait time.

## Where This Is Already Applied In This Extension

1. `main.py`: `_apply_extension_hooks(...)` asks for retry strategy and applies it per run.
2. `monitor.py`: retry delays are generated from the selected strategy before each retry attempt.
3. `monitor.py`: retry count and pacing follow the configured schedule (`no_retry`, `fixed`, `exponential_backoff`).

## Core Snippet

This loop is the strategy execution point in monitor retry handling, where each generated delay controls the next attempt and recovery cadence.

```python
for delay in get_retry_delays(spec):
	# run retry attempt
	# if success: break
```
## How To Run

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/05_retry_strategies
2. uv run main.py

## Test Run Instructions

1. cd Chapter-11-Planning-Systems-for-Agents/code/exercise1/extensions/05_retry_strategies
2. uv run --with pytest pytest -q test_extension.py
