"""Advisor tool — recommends actions and provides reasoning for a triaged ticket."""

import logging

from backend.schemas import Action, Category, Priority
from backend.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

_ACTION_MAP: dict[str, Action] = {a.value.lower(): a for a in Action}

SYSTEM_PROMPT = """You are an IT support advisor. Given a ticket's category, priority, and summary, recommend 1-3 concrete actions and explain your reasoning.

Available actions: "Restart Device", "Reset Password", "Escalate to L2 Support", "Escalate to L3/Security Team", "Install/Update Software", "Check Network Configuration", "Restore from Backup", "Schedule Remote Session", "Create Change Request", "Grant/Modify Access Permissions", "Monitor and Log", "Close - Self Resolved"

Respond with JSON only: {{"recommended_actions": ["..."], "reasoning": "..."}}"""

USER_TEMPLATE = (
    "Recommend actions for this triaged ticket:\n\n"
    "Category: {category}\n"
    "Priority: {priority}\n"
    "Summary: {summary}\n"
    "Original message: {message}"
)


def _match_action(raw: str) -> Action:
    key = raw.strip().lower()
    if key in _ACTION_MAP:
        return _ACTION_MAP[key]
    for name, action in _ACTION_MAP.items():
        if name in key or key in name:
            return action
    logger.warning("Unknown action '%s', defaulting to MONITOR_AND_LOG", raw)
    return Action.MONITOR_AND_LOG


def advise(
    llm: LLMClient,
    category: Category,
    priority: Priority,
    summary: str,
    message: str,
) -> tuple[list[Action], str]:
    """Recommend actions and provide reasoning for a triaged ticket.

    Returns:
        A tuple of (recommended_actions, reasoning).
    """
    prompt = USER_TEMPLATE.format(
        category=category.value,
        priority=priority.value,
        summary=summary,
        message=message,
    )
    data = llm.generate_json(SYSTEM_PROMPT, prompt)

    raw_actions = data.get("recommended_actions", [])
    if isinstance(raw_actions, str):
        raw_actions = [raw_actions]

    actions = [_match_action(a) for a in raw_actions[:3]]
    if not actions:
        actions = [Action.MONITOR_AND_LOG]

    reasoning = data.get("reasoning", "No reasoning provided.")
    return actions, reasoning
