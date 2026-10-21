"""Pydantic schemas and enums for the IT support triage system."""

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class Category(str, Enum):
    """IT support ticket categories."""

    HARDWARE = "Hardware Issue"
    SOFTWARE = "Software Issue"
    NETWORK = "Network/Connectivity"
    ACCOUNT_ACCESS = "Account/Access"
    SECURITY = "Security Incident"
    EMAIL = "Email/Communication"
    DATA_BACKUP = "Data/Backup"
    PERFORMANCE = "Performance"
    OTHER = "Other"


class Priority(str, Enum):
    """Ticket priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Action(str, Enum):
    """Recommended actions for IT support tickets."""

    RESTART_DEVICE = "Restart Device"
    RESET_PASSWORD = "Reset Password"
    ESCALATE_L2 = "Escalate to L2 Support"
    ESCALATE_L3_SECURITY = "Escalate to L3/Security Team"
    INSTALL_UPDATE_SOFTWARE = "Install/Update Software"
    CHECK_NETWORK = "Check Network Configuration"
    RESTORE_BACKUP = "Restore from Backup"
    REMOTE_SESSION = "Schedule Remote Session"
    CREATE_CHANGE_REQUEST = "Create Change Request"
    GRANT_ACCESS = "Grant/Modify Access Permissions"
    MONITOR_AND_LOG = "Monitor and Log"
    CLOSE_SELF_RESOLVED = "Close - Self Resolved"


class TicketMessage(BaseModel):
    """A single IT support message to triage."""

    id: str = Field(..., description="Unique ticket identifier")
    message: str = Field(..., min_length=1, description="The support message content")
    sender: str = Field(default="unknown", description="Who sent the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the message was received",
    )


class TriageResult(BaseModel):
    """Result of triaging a single ticket."""

    ticket_id: str
    category: Category
    priority: Priority
    summary: str = Field(..., description="Brief summary of the issue")
    recommended_actions: list[Action] = Field(
        ..., min_length=1, max_length=3, description="Top 1-3 recommended actions"
    )
    reasoning: str = Field(..., description="Why this classification was chosen")


class TriageRequest(BaseModel):
    """API request to triage one or more tickets."""

    tickets: list[TicketMessage] = Field(
        ..., min_length=1, max_length=20, description="Tickets to triage (max 20)"
    )


class TriageResponse(BaseModel):
    """API response containing triage results."""

    results: list[TriageResult]
    model_used: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model: str
    ollama_connected: bool
