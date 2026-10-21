from __future__ import annotations

from dataclasses import dataclass, field

from backend.schemas import ActionType, Message, Role


@dataclass
class SessionMemory:
    messages: list[Message] = field(default_factory=list)
    pending_action: ActionType = ActionType.NONE
    pending_action_label: str | None = None

    def add_user_message(self, content: str) -> None:
        self.messages.append(Message(role=Role.USER, content=content))

    def add_assistant_message(self, content: str) -> None:
        self.messages.append(Message(role=Role.ASSISTANT, content=content))

    def recent_context(self, limit: int = 6) -> list[Message]:
        return self.messages[-limit:]

    def summary_text(self) -> str:
        if not self.messages:
            return "No conversation yet."
        snippets = [f"{message.role.value}: {message.content}" for message in self.recent_context(4)]
        return " | ".join(snippets)


class ShortTermMemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}

    def get_or_create(self, session_id: str) -> SessionMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemory()
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
