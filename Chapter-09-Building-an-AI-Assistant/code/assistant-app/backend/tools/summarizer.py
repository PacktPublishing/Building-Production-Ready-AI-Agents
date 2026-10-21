"""Summarizer tool — produces a concise summary of an IT support ticket."""

import logging

from backend.schemas import TicketMessage
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an IT support summarizer. Given a support message, produce a concise 1-2 sentence summary that captures the core problem and any urgency.

Respond with JSON only: {{"summary": "..."}}"""

USER_TEMPLATE = "Summarize this IT support ticket:\n\nFrom: {sender}\nMessage: {message}"


def summarize(llm: LLMClient, ticket: TicketMessage) -> str:
    """Generate a concise summary of the ticket."""
    prompt = USER_TEMPLATE.format(sender=ticket.sender, message=ticket.message)
    data = llm.generate_json(SYSTEM_PROMPT, prompt)
    return data.get("summary", "No summary available.")
