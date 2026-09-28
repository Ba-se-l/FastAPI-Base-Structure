from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.security import decode_access_token
from src.exc import InvalidCredentialsException
from src.settings import settings

if TYPE_CHECKING:
    from src.modules.user import User


_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f'{settings.api_prefix}/auth/login')


async def get_current_user(
    token: str = Depends(_oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Extracts and validates the current authenticated user from the JWT token.

    This is a FastAPI dependency injected into every protected route.
    It performs three sequential validations:
    1. Decodes the JWT token and extracts the ``sub`` (user_id) claim.
    2. Fetches the user from the database by UUID.
    3. Verifies the user exists and is active.

    Args:
        token: The JWT bearer token extracted from the ``Authorization`` header.
        session: The async database session injected by FastAPI.

    Returns:
        The authenticated ``User`` ORM instance.

    Raises:
        InvalidCredentialsException: If the token is invalid, the user
            does not exist, or the user is inactive.
    """
    # Step 1: Decode the JWT token — raises InvalidCredentialsException if invalid
    payload = decode_access_token(token=token)
    user_id = payload.sub

    if user_id is None:
        raise InvalidCredentialsException()

    # Lazy import to break module-level circular dependency
    from src.modules.user import UserRepository
    
    # Step 2: Fetch the user from the database
    user_repo = UserRepository(session=session) # type: ignore
    user = await user_repo.get_by_id(int(user_id))

    if user is None:
        raise InvalidCredentialsException()

    # Step 3: Verify the user is active
    if not user.is_active:
        raise InvalidCredentialsException()

    return user
