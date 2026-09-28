"""Authentication domain ORM models.

Defines the RefreshSession table for server-side refresh token
management, supporting revocation, rotation, and multi-device sessions.
"""


from typing import TYPE_CHECKING
from datetime import datetime


from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import BaseModel as Base, DateTimeMixin


if TYPE_CHECKING:
    from src.modules.user import User


class RefreshSession(Base, DateTimeMixin):
    """Represents a server-side refresh token session.

    Each row corresponds to one active refresh token issued to a user
    on a specific device. Sessions can be individually revoked or
    bulk-revoked per user.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: Foreign key reference to the owning user.
        refresh_token_jti: Unique JWT ID (jti claim) of the refresh token.
        device_info: Optional device/client identifier string.
        is_revoked: Whether this session has been explicitly revoked.
        expires_at: UTC timestamp when the refresh token expires.
        user: SQLAlchemy relationship back to the User model.
    """

    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    refresh_token_jti: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    device_info: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="refresh_sessions")
