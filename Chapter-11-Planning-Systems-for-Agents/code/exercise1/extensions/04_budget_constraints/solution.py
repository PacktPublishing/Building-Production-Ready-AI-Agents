"""Where to put this:
- `BudgetPolicy`, `estimate_trip_cost`, `enforce_budget` belong in `monitor.py`
- Call `enforce_budget(...)` inside `Monitor.oversee_execution(...)`
- On budget failure, trigger replanning before final itinerary output
"""

from dataclasses import dataclass


# Add in `monitor.py` near other policy models.
@dataclass
class BudgetPolicy:
    max_total_usd: int


# Add in `monitor.py` as a helper used during validation.
def estimate_trip_cost(flight_usd: int, hotel_nights: int, hotel_per_night: int) -> int:
    return flight_usd + (hotel_nights * hotel_per_night)


# Add in `monitor.py` and call from `oversee_execution`.
def enforce_budget(policy: BudgetPolicy, estimated_total: int) -> tuple[bool, str]:
    if estimated_total <= policy.max_total_usd:
        return True, f"Within budget: ${estimated_total} <= ${policy.max_total_usd}"
    return False, f"Over budget: ${estimated_total} > ${policy.max_total_usd}"


# Place these lines in `monitor.py` inside `oversee_execution(...)` after step results:
# ok, reason = enforce_budget(policy, total)
# if not ok: trigger replanning with cheaper options
