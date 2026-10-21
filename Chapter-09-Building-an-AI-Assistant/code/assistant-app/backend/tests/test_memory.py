"""Tests for memory modules."""

import json
import tempfile
from pathlib import Path

from backend.schemas import Action, Category, Priority, TriageResult
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory


def _make_result(ticket_id: str = "T-1") -> TriageResult:
    return TriageResult(
        ticket_id=ticket_id,
        category=Category.HARDWARE,
        priority=Priority.HIGH,
        summary="Test summary.",
        recommended_actions=[Action.RESTART_DEVICE],
        reasoning="Test reasoning.",
    )


class TestShortTermMemory:
    def test_add_and_retrieve(self):
        mem = ShortTermMemory()
        mem.add(_make_result("T-1"))
        mem.add(_make_result("T-2"))

        assert mem.count == 2
        assert mem.get_by_id("T-1").ticket_id == "T-1"

    def test_max_items_enforced(self):
        mem = ShortTermMemory(max_items=3)
        for i in range(5):
            mem.add(_make_result(f"T-{i}"))

        assert mem.count == 3
        assert mem.get_by_id("T-0") is None  # evicted
        assert mem.get_by_id("T-4") is not None  # kept

    def test_clear(self):
        mem = ShortTermMemory()
        mem.add(_make_result())
        mem.clear()
        assert mem.count == 0


class TestLongTermMemory:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "history.json"
        mem = LongTermMemory(path=path)

        mem.save(_make_result("T-1"))
        mem.save(_make_result("T-2"))

        loaded = mem.load_all()
        assert len(loaded) == 2
        assert loaded[0].ticket_id == "T-1"

    def test_save_batch(self, tmp_path):
        path = tmp_path / "history.json"
        mem = LongTermMemory(path=path)

        mem.save_batch([_make_result("T-1"), _make_result("T-2")])
        assert mem.count == 2

    def test_clear(self, tmp_path):
        path = tmp_path / "history.json"
        mem = LongTermMemory(path=path)
        mem.save(_make_result())
        mem.clear()
        assert mem.count == 0

    def test_handles_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        mem = LongTermMemory(path=path)
        assert mem.load_all() == []
