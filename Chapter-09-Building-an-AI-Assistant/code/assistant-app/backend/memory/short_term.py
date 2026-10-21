"""Short-term memory — holds the current triage session context."""

from backend.schemas import TriageResult


class ShortTermMemory:
    """In-memory store for the current triage session.

    Keeps recent triage results so the assistant can reference
    previous decisions within the same session (e.g., for follow-up
    questions or batch-level insights).
    """

    def __init__(self, max_items: int = 100) -> None:
        self._results: list[TriageResult] = []
        self._max_items = max_items

    def add(self, result: TriageResult) -> None:
        self._results.append(result)
        if len(self._results) > self._max_items:
            self._results = self._results[-self._max_items :]

    def get_all(self) -> list[TriageResult]:
        return list(self._results)

    def get_by_id(self, ticket_id: str) -> TriageResult | None:
        for r in reversed(self._results):
            if r.ticket_id == ticket_id:
                return r
        return None

    def clear(self) -> None:
        self._results.clear()

    @property
    def count(self) -> int:
        return len(self._results)
