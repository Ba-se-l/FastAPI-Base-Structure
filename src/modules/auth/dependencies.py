from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.exc import AccessDeniedException, InactiveEntityException, InvalidCredentialsException
from src.security import decode_access_token
from src.settings import settings
from src.share import Roles

if TYPE_CHECKING:
    from src.modules.user import User


_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f'{settings.api_prefix}/auth/login')


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Extracts and validates the current authenticated user from the JWT token.

    Args:
        token: The JWT bearer token extracted from the Authorization header.
        session: The async database session injected by FastAPI.

    Returns:
        The authenticated User ORM instance.

    Raises:
        InvalidCredentialsException: If the token is invalid or the user does not exist.
        InactiveEntityException: If the user account has been deactivated.
    """
    payload = decode_access_token(token=token)
    user_id = payload.sub

    if user_id is None:
        raise InvalidCredentialsException()

    # Lazy import to break module-level circular dependency
    from src.modules.user import UserRepository

    user_repo = UserRepository(session=session)
    user = await user_repo.get_by_id(int(user_id))

    if user is None:
        raise InvalidCredentialsException()

    if not user.is_active:
        raise InactiveEntityException(entity='User', identifier=str(user.id))

    return user


async def require_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures that the authenticated user is currently active.

    Args:
        current_user: Authenticated user injected by FastAPI.

    Returns:
        The active User instance.

    Raises:
        InactiveEntityException: If user is inactive.
    """
    if not current_user.is_active:
        raise InactiveEntityException(entity='User', identifier=str(current_user.id))
    return current_user


def require_role(*allowed_roles: Roles) -> Callable[[User], Awaitable[User]]:
    """Dependency factory that enforces Role-Based Access Control (RBAC).

    Args:
        *allowed_roles: One or more authorized Roles required to access the endpoint.

    Returns:
        An async FastAPI dependency callable validating user role.
    """

    async def _role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            allowed_names = [role.value for role in allowed_roles]
            raise AccessDeniedException(
                f"Operation requires one of the following roles: {allowed_names}."
            )
        return current_user

    return _role_checker
