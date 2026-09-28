from enum import StrEnum


class TokenType(StrEnum):
    """Token type enumeration for JWT authentication."""

    ACCESS = 'access'
    """Short-lived access token for API authorization."""

    REFRESH = 'refresh'
    """Long-lived refresh token for renewing access tokens."""


class Roles(StrEnum):
    """User roles for role-based access control (RBAC)."""

    ADMIN = 'admin'
    """Administrator with elevated privileges."""

    USER = 'user'
    """Standard authenticated user."""