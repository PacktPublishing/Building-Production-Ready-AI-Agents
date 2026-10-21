from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolName(str, Enum):
    NETWORK_DIAGNOSTIC = "network_diagnostic"
    ACCOUNT_LOOKUP = "account_lookup"
    GENERAL_GUIDANCE = "general_guidance"


class ActionType(str, Enum):
    NONE = "none"
    RESTART_NETWORK = "restart_network"


class ToolResult(BaseModel):
    tool_name: ToolName
    output: str
    requires_confirmation: bool = False
    action_type: ActionType = ActionType.NONE
    action_label: str | None = None


class AssistantResponse(BaseModel):
    reply: str
    selected_tool: ToolName
    tool_output: str
    used_memory: bool
    needs_confirmation: bool = False
    pending_action: ActionType = ActionType.NONE
    pending_action_label: str | None = None
    session_summary: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ConfirmRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    approve: bool


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama_connected: bool


class SessionStateResponse(BaseModel):
    session_id: str
    messages: list[Message]
    pending_action: ActionType = ActionType.NONE
    pending_action_label: str | None = None
