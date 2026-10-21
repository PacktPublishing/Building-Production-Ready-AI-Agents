"""Assistant — orchestrates the triage pipeline.

Supports two modes:
- fast (default): Single LLM call for classify + summarize + advise (~3x faster)
- detailed: Three separate LLM calls for maximum accuracy
"""

import logging
import time
from collections.abc import Generator

from backend.schemas import (
    Action,
    Category,
    Priority,
    TicketMessage,
    TriageResult,
)
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory
from backend.tools.classifier import classify
from backend.tools.summarizer import summarize
from backend.tools.advisor import advise
from backend.tools.triage_combined import triage_combined
from backend.utils.config import Settings
from backend.utils.llm_client import LLMClient, LLMClientError

logger = logging.getLogger(__name__)


class Assistant:
    """Orchestrates the full triage pipeline using individual tools."""

    def __init__(self, settings: Settings) -> None:
        self._llm = LLMClient(settings)
        self._short_term = ShortTermMemory()
        self._long_term = LongTermMemory()

    @property
    def model_name(self) -> str:
        return self._llm.model_name

    async def check_health(self) -> bool:
        return await self._llm.check_connection()

    def triage_ticket(
        self, ticket: TicketMessage, *, detailed: bool = False
    ) -> TriageResult:
        """Run triage on a single ticket.

        Args:
            ticket: The support ticket to triage.
            detailed: If True, uses 3 separate LLM calls (slower, more thorough).
                      If False, uses a single combined call (~3x faster).
        """
        if detailed:
            category, priority = classify(self._llm, ticket)
            summary = summarize(self._llm, ticket)
            actions, reasoning = advise(
                self._llm, category, priority, summary, ticket.message
            )
        else:
            category, priority, summary, actions, reasoning = triage_combined(
                self._llm, ticket
            )

        result = TriageResult(
            ticket_id=ticket.id,
            category=category,
            priority=priority,
            summary=summary,
            recommended_actions=actions,
            reasoning=reasoning,
        )

        self._short_term.add(result)
        self._long_term.save(result)

        return result

    def triage_batch(
        self, tickets: list[TicketMessage], *, detailed: bool = False
    ) -> tuple[list[TriageResult], float]:
        """Triage multiple tickets, returning results and elapsed time in ms."""
        start = time.perf_counter()
        results: list[TriageResult] = []

        for ticket in tickets:
            try:
                result = self.triage_ticket(ticket, detailed=detailed)
                results.append(result)
            except LLMClientError as exc:
                logger.error("Failed to triage ticket %s: %s", ticket.id, exc)
                fallback = TriageResult(
                    ticket_id=ticket.id,
                    category=Category.OTHER,
                    priority=Priority.MEDIUM,
                    summary=f"Triage failed: {exc}",
                    recommended_actions=[Action.ESCALATE_L2],
                    reasoning="Automatic fallback due to LLM error.",
                )
                results.append(fallback)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return results, elapsed_ms

    def triage_stream(
        self, tickets: list[TicketMessage], *, detailed: bool = False
    ) -> Generator[TriageResult, None, None]:
        """Yield triage results one at a time for streaming."""
        for ticket in tickets:
            try:
                yield self.triage_ticket(ticket, detailed=detailed)
            except LLMClientError as exc:
                logger.error("Failed to triage ticket %s: %s", ticket.id, exc)
                yield TriageResult(
                    ticket_id=ticket.id,
                    category=Category.OTHER,
                    priority=Priority.MEDIUM,
                    summary=f"Triage failed: {exc}",
                    recommended_actions=[Action.ESCALATE_L2],
                    reasoning="Automatic fallback due to LLM error.",
                )

    @property
    def session_history(self) -> list[TriageResult]:
        """Return all results from the current session."""
        return self._short_term.get_all()
