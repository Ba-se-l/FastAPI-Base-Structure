from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class LogResponse(BaseModel):
    """Public serialization model for audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    """Database primary key record ID."""

    event_type: str
    """Categorized action tag."""

    severity: str
    """Severity classification level."""

    message: str
    """Human-readable narrative description."""

    user_id: str | None
    """Associated actor identifier."""

    request_id: str | None
    """Correlation tracing ID."""

    ip_address: str | None
    """Client IP address."""

    user_agent: str | None
    """Client User-Agent header string."""

    extra_data: dict[str, Any] | None
    """Arbitrary structured metadata dictionary."""

    created_at: datetime
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
