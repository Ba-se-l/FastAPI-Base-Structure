import logging
from pathlib import Path

import casbin
from casbin_async_sqlalchemy_adapter import Adapter
from sqlalchemy.ext.asyncio import AsyncEngine

from .casbin_rule import CasbinRule

logger = logging.getLogger(__name__)

RBAC_MODEL_PATH: Path = Path(__file__).with_name('rbac_model.conf')
USER_SUBJECT_PREFIX: str = 'user:'
WILDCARD: str = '*'

type PolicyRule = tuple[str, str, str]

DEFAULT_POLICIES: tuple[PolicyRule, ...] = (
    ('admin', WILDCARD, WILDCARD),
)


class AuthorizationNotInitializedError(RuntimeError):
    """Raised when an authorization check runs before AuthorizationService is initialized."""


class AuthorizationService:
    """Process-wide facade over a single cached PyCasbin AsyncEnforcer instance."""

    _enforcer: casbin.AsyncEnforcer | None = None

    @classmethod
    async def initialize(cls, engine: AsyncEngine) -> casbin.AsyncEnforcer:
        """Initializes the Casbin AsyncEnforcer bound to the specified database engine.

        Constructs the SQLAlchemy adapter using the existing CasbinRule model and
        loads all active policies from the database into RAM cache.

        Args:
            engine: The SQLAlchemy AsyncEngine instance to bind the adapter to.

        Returns:
            The initialized and loaded AsyncEnforcer instance.
        """
        adapter = Adapter(
            engine=engine,
            db_class=CasbinRule,
        )

        enforcer = casbin.AsyncEnforcer(str(RBAC_MODEL_PATH), adapter)
        await enforcer.load_policy()

        cls._enforcer = enforcer

        if not enforcer.get_policy():
            logger.warning(
                'AuthorizationService loaded zero policies from storage. '
                'All protected operations will fail closed.'
            )

        return enforcer

    @classmethod
    def get_enforcer(cls) -> casbin.AsyncEnforcer:
        """Retrieves the active cached AsyncEnforcer instance.

        Returns:
            The loaded AsyncEnforcer singleton.

        Raises:
            AuthorizationNotInitializedError: If called before initialize().
        """
        if cls._enforcer is None:
            raise AuthorizationNotInitializedError(
                'AuthorizationService has not been initialized. '
                'Call AuthorizationService.initialize(engine) during application startup.'
            )
        return cls._enforcer

    @classmethod
    async def reload(cls) -> None:
        """Reloads all policies from the database into the in-memory cache."""
        enforcer = cls.get_enforcer()
        await enforcer.load_policy()

    @classmethod
    async def seed_default_policies(cls) -> int:
        """Idempotently ensures baseline authorization policies are persisted in the database.

        Returns:
            The number of newly inserted policy rules.
        """
        enforcer = cls.get_enforcer()
        added_count = 0

        for rule in DEFAULT_POLICIES:
            if not enforcer.has_policy(*rule):
                await enforcer.add_policy(*rule)
                added_count += 1

        return added_count

    @staticmethod
    def user_subject(user_id: int) -> str:
        """Formats an integer user identifier into a Casbin subject token.

        Args:
            user_id: Integer primary key of the user.

        Returns:
            Namespaced user subject string (e.g. 'user:42').
        """
        return f'{USER_SUBJECT_PREFIX}{user_id}'

    @classmethod
    def is_allowed(
        cls,
        *,
        user_id: int,
        role: str,
        resource: str,
        action: str,
    ) -> bool:
        """Evaluates whether an actor has permission to perform an action on a resource.

        Evaluates two identity vectors in sequence:
        1. Role-based check: Checks the user's primary role (Compatibility Projection).
        2. Subject-based check: Checks user-specific grants or groupings ('user:<id>').

        Args:
            user_id: Primary key of the authenticated user.
            role: The primary role name of the user (e.g. 'admin', 'user').
            resource: Target resource token.
            action: Action token.

        Returns:
            True if permission is granted by any active policy; False otherwise.
        """
        enforcer = cls.get_enforcer()

        # 1. Compatibility projection: evaluate user's primary role directly
        if enforcer.enforce(role, resource, action):
            return True

        # 2. Per-user grants: evaluate specific user token ('user:<id>')
        return enforcer.enforce(cls.user_subject(user_id), resource, action)

    @classmethod
    def reset(cls) -> None:
        """Resets the singleton enforcer reference. Intended strictly for test teardown."""
        cls._enforcer = None