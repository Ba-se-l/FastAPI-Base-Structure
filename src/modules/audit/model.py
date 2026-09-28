from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import BaseModel as Base


class AuditLog(Base):
    """Immutable audit log entity for security, compliance, and telemetry tracking.

    Designed to be completely portable and decoupled from user domain models;
    stores user_id as a generic indexed string identifier.

    Attributes:
        id: Primary key unique identifier.
        event_type: Machine-readable categorized action tag.
        severity: Severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        message: Human-readable narrative description.
        user_id: Optional string identifier of the responsible actor.
        request_id: Optional correlation ID for tracing.
        ip_address: Optional client IPv4 or IPv6 address.
        user_agent: Optional client device or browser string.
        extra_data: Flexible JSON dictionary for structured metadata.
        created_at: Immutable UTC timestamp of event creation.
    """

    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index('ix_audit_user_created', 'user_id', 'created_at'),
        Index('ix_audit_event_created', 'event_type', 'created_at'),
        Index('ix_audit_severity_created', 'severity', 'created_at'),
    )

    def __repr__(self) -> str:
        return (
            f"AuditLog(id={self.id}, event_type='{self.event_type}', "
            f"severity='{self.severity}', user_id='{self.user_id}')"
        )
