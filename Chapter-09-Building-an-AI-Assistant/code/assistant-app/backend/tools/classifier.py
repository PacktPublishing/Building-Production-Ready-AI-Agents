"""Classifier tool — determines the category and priority of an IT support ticket."""

import logging

from backend.schemas import Category, Priority, TicketMessage
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CATEGORY_MAP: dict[str, Category] = {c.value.lower(): c for c in Category}
_PRIORITY_MAP: dict[str, Priority] = {p.value.lower(): p for p in Priority}

SYSTEM_PROMPT = """You are an IT support ticket classifier. Given a support message, determine its category and priority.

Categories: "Hardware Issue", "Software Issue", "Network/Connectivity", "Account/Access", "Security Incident", "Email/Communication", "Data/Backup", "Performance", "Other"

Priorities:
- critical: System-wide outage, security breach, data loss affecting multiple users
- high: Single user unable to work, security concern, urgent deadline impact
- medium: Degraded functionality, workaround available, non-urgent access request
- low: Cosmetic issue, general question, enhancement request

Respond with JSON only: {{"category": "...", "priority": "..."}}"""

USER_TEMPLATE = "Classify this IT support ticket:\n\nFrom: {sender}\nMessage: {message}"


def _match_category(raw: str) -> Category:
    key = raw.strip().lower()
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    for name, cat in _CATEGORY_MAP.items():
        if name in key or key in name:
            return cat
    logger.warning("Unknown category '%s', defaulting to OTHER", raw)
    return Category.OTHER


def _match_priority(raw: str) -> Priority:
    key = raw.strip().lower()
    if key in _PRIORITY_MAP:
        return _PRIORITY_MAP[key]
    logger.warning("Unknown priority '%s', defaulting to MEDIUM", raw)
    return Priority.MEDIUM


def classify(llm: LLMClient, ticket: TicketMessage) -> tuple[Category, Priority]:
    """Classify a ticket into a category and priority level."""
    prompt = USER_TEMPLATE.format(sender=ticket.sender, message=ticket.message)
    data = llm.generate_json(SYSTEM_PROMPT, prompt)

    category = _match_category(data.get("category", "Other"))
    priority = _match_priority(data.get("priority", "medium"))
    return category, priority
