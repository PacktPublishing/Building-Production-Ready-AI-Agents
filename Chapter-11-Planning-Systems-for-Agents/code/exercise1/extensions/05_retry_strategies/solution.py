"""Where to put this:
- Put `RetrySpec` and `get_retry_delays(...)` in `monitor.py`
- Use inside retry loop in `Monitor.oversee_execution(...)`
- Optionally store strategy in `StepPolicy` in `models.py`
"""

from dataclasses import dataclass


# Add in `monitor.py` (or `models.py` if shared broadly).
@dataclass
class RetrySpec:
    strategy: str
    attempts: int


# Add in `monitor.py` and call from retry branch.
def get_retry_delays(spec: RetrySpec) -> list[int]:
    if spec.strategy == "no_retry":
        return []
    if spec.strategy == "fixed":
        return [1 for _ in range(spec.attempts)]
    if spec.strategy == "exponential_backoff":
        return [2 ** i for i in range(spec.attempts)]
    return []


# Place these lines in `monitor.py` retry branch:
# for delay in get_retry_delays(spec):
#   run_retry_attempt()
#   if success: break
