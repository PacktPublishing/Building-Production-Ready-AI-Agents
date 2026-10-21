"""Tests for individual tools (classifier, summarizer, advisor)."""

from unittest.mock import MagicMock

from backend.schemas import Action, Category, Priority, TicketMessage
from backend.tools.classifier import classify, _match_category, _match_priority
from backend.tools.summarizer import summarize
from backend.tools.advisor import advise, _match_action


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class TestMatchCategory:
    def test_exact_match(self):
        assert _match_category("Hardware Issue") == Category.HARDWARE

    def test_case_insensitive(self):
        assert _match_category("hardware issue") == Category.HARDWARE

    def test_fuzzy_match(self):
        assert _match_category("network") == Category.NETWORK

    def test_unknown_defaults_to_other(self):
        assert _match_category("completely unknown") == Category.OTHER


class TestMatchPriority:
    def test_exact_match(self):
        assert _match_priority("critical") == Priority.CRITICAL

    def test_case_insensitive(self):
        assert _match_priority("HIGH") == Priority.HIGH

    def test_unknown_defaults_to_medium(self):
        assert _match_priority("urgent") == Priority.MEDIUM


class TestClassify:
    def test_classify_returns_category_and_priority(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "category": "Hardware Issue",
            "priority": "high",
        }

        ticket = TicketMessage(id="T-1", message="Laptop broken", sender="user")
        cat, pri = classify(mock_llm, ticket)

        assert cat == Category.HARDWARE
        assert pri == Priority.HIGH
        mock_llm.generate_json.assert_called_once()


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_summarize_returns_text(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "summary": "Laptop not booting after update."
        }

        ticket = TicketMessage(id="T-1", message="Laptop broken", sender="user")
        result = summarize(mock_llm, ticket)

        assert result == "Laptop not booting after update."

    def test_summarize_fallback_on_missing_key(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {}

        ticket = TicketMessage(id="T-1", message="Laptop broken", sender="user")
        result = summarize(mock_llm, ticket)

        assert result == "No summary available."


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

class TestMatchAction:
    def test_exact_match(self):
        assert _match_action("Reset Password") == Action.RESET_PASSWORD

    def test_case_insensitive(self):
        assert _match_action("reset password") == Action.RESET_PASSWORD

    def test_fuzzy_match(self):
        assert _match_action("restart") == Action.RESTART_DEVICE

    def test_unknown_defaults_to_monitor(self):
        assert _match_action("do something strange") == Action.MONITOR_AND_LOG


class TestAdvise:
    def test_advise_returns_actions_and_reasoning(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "recommended_actions": ["Restart Device", "Schedule Remote Session"],
            "reasoning": "Hardware issue needs hands-on support.",
        }

        actions, reasoning = advise(
            mock_llm, Category.HARDWARE, Priority.HIGH,
            "Laptop won't boot", "My laptop is dead"
        )

        assert Action.RESTART_DEVICE in actions
        assert Action.REMOTE_SESSION in actions
        assert "hands-on" in reasoning

    def test_advise_fallback_on_empty_actions(self):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "recommended_actions": [],
            "reasoning": "Unknown.",
        }

        actions, _ = advise(
            mock_llm, Category.OTHER, Priority.LOW,
            "General question", "How do I reset?"
        )

        assert actions == [Action.MONITOR_AND_LOG]
