from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SQLEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import BaseModel as Base, DateTimeMixin
from src.share import Roles

if TYPE_CHECKING:
    from src.modules.auth.model import RefreshSession


class User(Base, DateTimeMixin):
    """User account entity.

    Attributes:
        id: Primary key unique identifier.
        name: Full display name of the user.
        email: Unique user email address for authentication.
        hashed_password: Salted and hashed password string.
        role: Access control role (admin or user).
        is_active: Whether the account is active.
        refresh_sessions: Associated active refresh sessions.
    """

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Roles] = mapped_column(
        SQLEnum(Roles, native_enum=False, length=20),
        default=Roles.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Relationships ---
    refresh_sessions: Mapped[list['RefreshSession']] = relationship(
        'RefreshSession',
        back_populates='user',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name}, email={self.email}, role={self.role})"