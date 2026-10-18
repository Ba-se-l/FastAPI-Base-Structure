from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.share import (
    AUDIT_IP_MAX,
    AUDIT_REQUEST_ID_MAX,
    AUDIT_USER_AGENT_MAX,
    AUDIT_USER_ID_MAX,
)
from .enum import ExportFormat, LogSeverity


class LogEvent(BaseModel):
    """Payload contract for registering a new audit or telemetry event."""

    event_type: str = Field(..., min_length=1, max_length=100)
    """Categorized action tag (e.g. AUTH_LOGIN_SUCCESS, USER_REGISTERED)."""

    severity: LogSeverity = LogSeverity.INFO
    """Severity classification level."""

    message: str = Field(..., min_length=1)
    """Human-readable description of the event."""

    user_id: str | None = None
    """Optional identifier of the actor (integer string, UUID, or system key)."""

    request_id: str | None = None
    """Correlation ID from HTTP request tracing."""

    ip_address: str | None = None
    """Client IPv4 or IPv6 address."""

    user_agent: str | None = None
    """Client device or browser User-Agent string."""

    extra_data: dict[str, Any] | None = None
    """Structured arbitrary metadata dictionary."""

    @field_validator('user_id', mode='before')
    @classmethod
    def truncate_user_id(cls, v: Any) -> str | None:
        """Truncates user_id to AUDIT_USER_ID_MAX to prevent DB column overflow."""
        if v is None:
            return None
        return str(v)[:AUDIT_USER_ID_MAX]

    @field_validator('request_id', mode='before')
    @classmethod
    def truncate_request_id(cls, v: Any) -> str | None:
        """Truncates request_id to AUDIT_REQUEST_ID_MAX to prevent DB column overflow."""
        if v is None:
            return None
        return str(v)[:AUDIT_REQUEST_ID_MAX]

    @field_validator('ip_address', mode='before')
    @classmethod
    def truncate_ip_address(cls, v: Any) -> str | None:
        """Truncates ip_address to AUDIT_IP_MAX to prevent DB column overflow."""
        if v is None:
            return None
        return str(v)[:AUDIT_IP_MAX]

    @field_validator('user_agent', mode='before')
    @classmethod
    def truncate_user_agent(cls, v: Any) -> str | None:
        """Truncates user_agent to AUDIT_USER_AGENT_MAX to prevent DB column overflow."""
        if v is None:
            return None
        return str(v)[:AUDIT_USER_AGENT_MAX]



class LogResponse(BaseModel):
    """Public serialization model for audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    """Database primary key record ID (None if database persistence is disabled)."""

    event_type: str
    """Categorized action tag."""

    severity: str
    """Severity classification level."""

    message: str
    """Human-readable narrative description."""

    user_id: str | None = None
    """Associated actor identifier."""

    request_id: str | None = None
    """Correlation tracing ID."""

    ip_address: str | None = None
    """Client IP address."""

    user_agent: str | None = None
    """Client User-Agent header string."""

    extra_data: dict[str, Any] | None = None
    """Arbitrary structured metadata dictionary."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Immutable UTC timestamp when record was persisted."""


class LogQueryFilter(BaseModel):
    """Filter parameters for querying audit logs."""

    user_id: str | None = None
    """Filter by specific actor identifier."""

    event_type: str | None = None
    """Filter by exact event category tag."""

    severity: LogSeverity | None = None
    """Filter by severity level."""

    from_date: datetime | None = None
    """Lower bound UTC creation timestamp."""

    to_date: datetime | None = None
    """Upper bound UTC creation timestamp."""

    search: str | None = None
    """Case-insensitive substring search across the message field."""


class LogExportParams(BaseModel):
    """Parameters for exporting audit log records."""

    format: ExportFormat = ExportFormat.JSON
    """Target file serialization format."""

    user_id: str | None = None
    """Filter export to a specific user identifier."""

    event_type: str | None = None
    """Filter export by event category tag."""

    severity: LogSeverity | None = None
    """Filter export by severity level."""

    from_date: datetime | None = None
    """Filter export from specific start date."""

    to_date: datetime | None = None
    """Filter export up to specific end date."""
