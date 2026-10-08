from enum import StrEnum


class LogSeverity(StrEnum):
    """Severity classification for audit and telemetry events."""

    DEBUG = 'DEBUG'
    """Fine-grained diagnostic information for debugging."""

    INFO = 'INFO'
    """Standard operational milestones and normal state changes."""

    WARNING = 'WARNING'
    """Unexpected condition that does not halt immediate execution."""

    ERROR = 'ERROR'
    """Operation failed or unexpected exception was caught."""

    CRITICAL = 'CRITICAL'
    """Severe failure compromising system security or stability."""


class LogAction(StrEnum):
    """Standard categorized action identifiers for security and audit trails."""

    AUTH_LOGIN_SUCCESS = 'AUTH_LOGIN_SUCCESS'
    """User successfully authenticated and received token pair."""

    AUTH_LOGIN_FAILED = 'AUTH_LOGIN_FAILED'
    """Authentication attempt failed due to invalid credentials."""

    AUTH_LOGOUT = 'AUTH_LOGOUT'
    """User terminated an active session."""

    AUTH_TOKEN_ROTATED = 'AUTH_TOKEN_ROTATED'
    """Refresh token was rotated and exchanged for new token pair."""

    AUTH_TOKEN_REVOKED = 'AUTH_TOKEN_REVOKED'
    """Token revocation triggered or replay attack detected."""

    AUTH_PASSWORD_CHANGED = 'AUTH_PASSWORD_CHANGED'
    """User credentials were updated and sessions invalidated."""

    USER_REGISTERED = 'USER_REGISTERED'
    """New user account was provisioned."""

    USER_UPDATED = 'USER_UPDATED'
    """User profile or attributes were updated."""

    USER_DEACTIVATED = 'USER_DEACTIVATED'
    """User account was soft-deleted or deactivated."""

    SECURITY_ACCESS_DENIED = 'SECURITY_ACCESS_DENIED'
    """Unauthorized request blocked by RBAC or permissions."""

    SYSTEM_ERROR = 'SYSTEM_ERROR'
    """Internal server failure or uncaught runtime exception."""

    CUSTOM = 'CUSTOM'
    """Domain-specific or application-defined custom action."""


class ExportFormat(StrEnum):
    """Supported output serialization formats for audit log export."""

    JSON = 'json'
    """JSON Lines (NDJSON) or JSON array format."""

    TXT = 'txt'
    """Human-readable structured plain-text log format."""

    MARKDOWN = 'md'
    """GitHub-flavored markdown table representation."""
