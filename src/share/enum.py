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


class UserAction(StrEnum):
    """Finite set of user-targeted operations subject to authorization."""

    VIEW = 'view'
    MODIFY = 'modify'
    CHANGE_ROLE = 'change_role'
    LOGIN = 'login'
    REFRESH = 'refresh'


class Resource(StrEnum):
    """Protected resource namespaces evaluated by the Casbin policy engine."""

    USERS = 'users'
    """User accounts and profiles namespace."""

    AUDIT = 'audit'
    """Audit log records and exports namespace."""


class Action(StrEnum):
    """Operations that can be authorized on a Resource through Casbin policies."""

    CREATE = 'create'
    """Create new records."""

    READ = 'read'
    """Read or list records."""

    UPDATE = 'update'
    """Modify existing records."""

    DELETE = 'delete'
    """Delete records."""

    EXPORT = 'export'
    """Export records to downloadable formats."""

    ASSIGN_ROLE = 'assign_role'
    """Change the access role of a user."""