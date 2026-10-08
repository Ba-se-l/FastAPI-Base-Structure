from dataclasses import dataclass
from enum import StrEnum

from src.share import DomainEvent

__all__ = (
    'AuthAction',
    'AuthAllSessionsRevoked',
    'AuthEmailAlreadyRegistered',
    'AuthEmailNotFound',
    'AuthInactiveUserRejected',
    'AuthInvalidPassword',
    'AuthLoggedIn',
    'AuthLoggedOut',
    'AuthRefreshSessionExpired',
    'AuthRefreshSessionNotFound',
    'AuthRegistrationFailed',
    'AuthTokenPairIssued',
    'AuthTokenReplayDetected',
    'AuthTokenRotated',
    'AuthUserRegistered',
)


class AuthAction(StrEnum):
    """Authentication action attempted on an inactive account."""

    LOGIN = 'login'
    """User credential login attempt."""

    REFRESH = 'refresh'
    """Session token renewal attempt."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthEmailAlreadyRegistered(DomainEvent):
    """A registration attempt specified an email that already exists."""

    user_id: int
    """Primary key of the existing user account."""

    email: str
    """Colliding email address."""

    name: str
    """Attempted display name."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthEmailNotFound(DomainEvent):
    """A login attempt specified an email address not present in the system."""

    email: str
    """Unregistered email address queried."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthRegistrationFailed(DomainEvent):
    """A registration transaction failed database constraints."""

    email: str
    """Attempted email address."""

    error: str
    """Database driver error message."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthInvalidPassword(DomainEvent):
    """A login attempt provided an incorrect password hash match."""

    user_id: int
    """Identifier of the targeted user account."""

    email: str
    """Email address of the targeted user account."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthInactiveUserRejected(DomainEvent):
    """An authentication request targeted a deactivated user account."""

    user_id: int
    """Identifier of the deactivated user account."""

    email: str
    """Email address of the deactivated user account."""

    action: AuthAction
    """Authentication operation that was rejected."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthRefreshSessionNotFound(DomainEvent):
    """A refresh token JTI could not be located in active sessions."""

    user_id: int
    """Identifier of the subject extracted from the token."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthRefreshSessionExpired(DomainEvent):
    """A refresh session exceeded its valid lifetime."""

    user_id: int
    """Identifier of the subject."""

    session_id: int
    """Database identifier of the expired refresh session."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthTokenReplayDetected(DomainEvent):
    """A previously revoked refresh token was submitted again."""

    user_id: int
    """Identifier of the subject targeted by the replay attempt."""

    session_id: int
    """Database identifier of the revoked refresh session."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthUserRegistered(DomainEvent):
    """A new user account was successfully registered."""

    user_id: int
    """Identifier of the newly created user."""

    email: str
    """Registered email address."""

    name: str
    """Registered display name."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthLoggedIn(DomainEvent):
    """A user successfully authenticated credentials."""

    user_id: int
    """Identifier of the authenticated user."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthTokenPairIssued(DomainEvent):
    """An access and refresh token pair was generated."""

    user_id: int
    """Identifier of the user receiving tokens."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthTokenRotated(DomainEvent):
    """A refresh session was rotated and a new token pair issued."""

    user_id: int
    """Identifier of the user receiving rotated tokens."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthLoggedOut(DomainEvent):
    """A single refresh session was explicitly revoked by the user."""

    user_id: int
    """Identifier of the user terminating the session."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthAllSessionsRevoked(DomainEvent):
    """All active refresh sessions for a user were revoked."""

    user_id: int
    """Identifier of the user revoking all devices."""


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthPasswordChanged(DomainEvent):
    """A user account password was successfully updated and sessions invalidated."""

    user_id: int
    """Identifier of the user who changed credentials."""

    email: str
    """Email address of the user."""