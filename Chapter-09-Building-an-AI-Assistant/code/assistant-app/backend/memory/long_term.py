"""Long-term memory — persists triage history to a JSON file."""

import json
import logging
from pathlib import Path

from backend.schemas import TriageResult

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "triage_history.json"


class LongTermMemory:
    """Persists triage results to disk as JSON.

    Enables pattern analysis across sessions — e.g., spotting repeat
    issues, tracking category distribution over time, or identifying
    frequent senders.
    """

    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, result: TriageResult) -> None:
        """Append a triage result to the history file."""
        history = self._load_raw()
        history.append(result.model_dump(mode="json"))
        self._write_raw(history)

    def save_batch(self, results: list[TriageResult]) -> None:
        """Append multiple triage results to the history file."""
        history = self._load_raw()
        history.extend(r.model_dump(mode="json") for r in results)
        self._write_raw(history)

    def load_all(self) -> list[TriageResult]:
        """Load all stored triage results."""
        return [TriageResult(**item) for item in self._load_raw()]

    def clear(self) -> None:
        """Clear the history file."""
        self._write_raw([])

    @property
    def count(self) -> int:
        return len(self._load_raw())

    def _load_raw(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load triage history: %s", exc)
            return []

    def _write_raw(self, data: list[dict]) -> None:
        self._path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
