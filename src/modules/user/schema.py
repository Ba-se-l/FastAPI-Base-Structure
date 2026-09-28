from datetime import datetime

from pydantic import BaseModel as Base, ConfigDict

from src.share import Roles


class UserResponse(Base):
    """User response representation for API boundaries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    """Unique identifier of the user."""

    name: str
    """Full display name."""

    email: str
    """User email address."""

    role: Roles
    """Assigned user role for authorization."""

    is_active: bool
    """Active status flag."""

    created_at: datetime
    """Account creation timestamp."""

    updated_at: datetime
    """Account last updated timestamp."""


class UserUpdate(Base):
    """Schema for updating user details."""

    name: str | None = None
    """Updated display name."""

    is_active: bool | None = None
    """Updated active status."""

    role: Roles | None = None
    """Updated access role."""
