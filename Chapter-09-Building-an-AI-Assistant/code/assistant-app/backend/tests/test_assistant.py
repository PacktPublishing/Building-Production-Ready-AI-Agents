"""Tests for the Assistant orchestrator."""

from unittest.mock import MagicMock, patch

from backend.schemas import (
    Action,
    Category,
    Priority,
    TicketMessage,
    TriageResult,
)
from backend.assistant import Assistant
from backend.utils.llm_client import LLMClientError


class TestAssistant:
    @patch("backend.assistant.LLMClient")
    def test_triage_ticket_fast_mode(self, MockLLMClient, settings):
        """Default fast mode uses a single combined LLM call."""
        mock_llm = MagicMock()
        mock_llm.model_name = "mistral:latest"
        mock_llm.generate_json.return_value = {
            "category": "Security Incident",
            "priority": "critical",
            "summary": "Phishing email impersonating CEO requesting wire transfer.",
            "recommended_actions": ["Escalate to L3/Security Team"],
            "reasoning": "Potential CEO fraud / business email compromise.",
        }
        MockLLMClient.return_value = mock_llm

        assistant = Assistant(settings)
        ticket = TicketMessage(
            id="T-003",
            message="Suspicious email from fake CEO",
            sender="carol@company.com",
        )

        result = assistant.triage_ticket(ticket)

        assert isinstance(result, TriageResult)
        assert result.category == Category.SECURITY
        assert result.priority == Priority.CRITICAL
        assert "Phishing" in result.summary
        assert Action.ESCALATE_L3_SECURITY in result.recommended_actions
        mock_llm.generate_json.assert_called_once()  # single call

    @patch("backend.assistant.LLMClient")
    def test_triage_ticket_detailed_mode(self, MockLLMClient, settings):
        """Detailed mode uses 3 separate LLM calls."""
        mock_llm = MagicMock()
        mock_llm.model_name = "mistral:latest"
        mock_llm.generate_json.side_effect = [
            {"category": "Security Incident", "priority": "critical"},
            {"summary": "Phishing email impersonating CEO requesting wire transfer."},
            {
                "recommended_actions": ["Escalate to L3/Security Team"],
                "reasoning": "Potential CEO fraud / business email compromise.",
            },
        ]
        MockLLMClient.return_value = mock_llm

        assistant = Assistant(settings)
        ticket = TicketMessage(
            id="T-003",
            message="Suspicious email from fake CEO",
            sender="carol@company.com",
        )

        result = assistant.triage_ticket(ticket, detailed=True)

        assert result.category == Category.SECURITY
        assert result.priority == Priority.CRITICAL
        assert "Phishing" in result.summary
        assert mock_llm.generate_json.call_count == 3  # classify + summarize + advise

    @patch("backend.assistant.LLMClient")
    def test_triage_batch_with_failure(self, MockLLMClient, settings):
        mock_llm = MagicMock()
        mock_llm.model_name = "mistral:latest"
        mock_llm.generate_json.side_effect = LLMClientError("timeout")
        MockLLMClient.return_value = mock_llm

        assistant = Assistant(settings)
        tickets = [
            TicketMessage(id="T-FAIL", message="Something broke", sender="user"),
        ]

        results, elapsed = assistant.triage_batch(tickets)

        assert len(results) == 1
        assert results[0].category == Category.OTHER
        assert Action.ESCALATE_L2 in results[0].recommended_actions
        assert elapsed > 0

    @patch("backend.assistant.LLMClient")
    def test_session_history_populated(self, MockLLMClient, settings):
        mock_llm = MagicMock()
        mock_llm.model_name = "mistral:latest"
        mock_llm.generate_json.return_value = {
            "category": "Software Issue",
            "priority": "medium",
            "summary": "App crash.",
            "recommended_actions": ["Install/Update Software"],
            "reasoning": "Bug.",
        }
        MockLLMClient.return_value = mock_llm

        assistant = Assistant(settings)
        ticket = TicketMessage(id="T-010", message="App crashes", sender="user")
        assistant.triage_ticket(ticket)

        history = assistant.session_history
        assert len(history) == 1
        assert history[0].ticket_id == "T-010"
