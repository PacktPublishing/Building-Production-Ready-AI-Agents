"""Combined triage tool — single LLM call for classify + summarize + advise.

This is ~3x faster than calling each tool separately since it makes
only one LLM roundtrip instead of three.
"""

import logging

from backend.schemas import Action, Category, Priority, TicketMessage
from backend.tools.classifier import _match_category, _match_priority
from backend.tools.advisor import _match_action
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """IT triage specialist. Classify and advise on the ticket.

Categories: Hardware Issue, Software Issue, Network/Connectivity, Account/Access, Security Incident, Email/Communication, Data/Backup, Performance, Other
Priorities: critical, high, medium, low
Actions: Restart Device, Reset Password, Escalate to L2 Support, Escalate to L3/Security Team, Install/Update Software, Check Network Configuration, Restore from Backup, Schedule Remote Session, Create Change Request, Grant/Modify Access Permissions, Monitor and Log, Close - Self Resolved

JSON: {"category":"...","priority":"...","summary":"one sentence","recommended_actions":["max 2"],"reasoning":"one sentence"}"""

USER_TEMPLATE = "Triage this IT support ticket:\n\nFrom: {sender}\nMessage: {message}"


def triage_combined(
    llm: LLMClient, ticket: TicketMessage
) -> tuple[Category, Priority, str, list[Action], str]:
    """Perform full triage in a single LLM call.

    Returns:
        Tuple of (category, priority, summary, actions, reasoning).
    """
    prompt = USER_TEMPLATE.format(sender=ticket.sender, message=ticket.message)
    data = llm.generate_json(SYSTEM_PROMPT, prompt)

    category = _match_category(data.get("category", "Other"))
    priority = _match_priority(data.get("priority", "medium"))
    summary = data.get("summary", "No summary available.")
    reasoning = data.get("reasoning", "No reasoning provided.")

    raw_actions = data.get("recommended_actions", [])
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]
    actions = [_match_action(a) for a in raw_actions[:3]]
    if not actions:
        actions = [Action.MONITOR_AND_LOG]

    return category, priority, summary, actions, reasoning
