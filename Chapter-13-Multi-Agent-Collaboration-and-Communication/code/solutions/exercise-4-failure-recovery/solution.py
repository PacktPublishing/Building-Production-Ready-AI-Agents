"""Exercise 4 solution: retry with backoff and checkpoint/resume.

Run:
    python solutions/exercise-4-failure-recovery.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Checkpoint:
    trace_id: str
    stage: str
    attempts: int


def retry_with_backoff(action, attempts: int = 3):
    delay_seconds = 1
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as exc:
            if attempt == attempts:
                raise RuntimeError(f"exhausted retries after {attempts} attempts") from exc
            print(f"attempt {attempt} failed, retrying in {delay_seconds}s")
            time.sleep(delay_seconds)
            delay_seconds *= 2


class FlakyFetcher:
    def __init__(self, fail_first_n: int) -> None:
        self.calls = 0
        self.fail_first_n = fail_first_n

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_first_n:
            raise ConnectionError("temporary upstream failure")
        return {"quoted_total": 1988, "currency": "USD"}


def save_checkpoint(cp: Checkpoint) -> None:
    print(f"checkpoint saved: trace={cp.trace_id} stage={cp.stage} attempts={cp.attempts}")


def resume_from_checkpoint(cp: Checkpoint) -> None:
    print(f"resumed: trace={cp.trace_id} from stage={cp.stage}")


def main() -> None:
    trace_id = "trip-2048"
    fetch_quotes = FlakyFetcher(fail_first_n=2)

    print("Failure recovery demo")
    print("---------------------")

    checkpoint = Checkpoint(trace_id=trace_id, stage="awaiting_research", attempts=0)
    save_checkpoint(checkpoint)

    quotes = retry_with_backoff(fetch_quotes, attempts=3)
    checkpoint = Checkpoint(trace_id=trace_id, stage="awaiting_policy", attempts=fetch_quotes.calls)
    save_checkpoint(checkpoint)

    resume_from_checkpoint(checkpoint)
    print(f"quotes recovered: {quotes}")


if __name__ == "__main__":
    main()
