from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from src.exc import (
    InvalidCredentialsException,
    TokenRevokedException,
)

from src.settings import settings
from src.modules.user import User, UserRepository, UserAlreadyExistsException, UserInactiveException
from .schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from .model import RefreshSession
from .repo import RefreshSessionRepository


async def _issue_token_pair(
    user_id: int,
    session: AsyncSession,
    device_info: str | None = None,
) -> TokenResponse:
    """Creates an access + refresh token pair and persists the refresh session.

    Args:
        user_id: The authenticated user's primary key.
        session: The active database session.
        device_info: Optional client device identifier.

    Returns:
        A TokenResponse containing both tokens.
    """
    # Step 1: Generate access token
    access_token = create_access_token(user_id=user_id)

    # Step 2: Generate refresh token + JTI
    refresh_token, jti = create_refresh_token(user_id=user_id)

    # Step 3: Persist refresh session to database
    refresh_repo = RefreshSessionRepository(session=session) # type: ignore
    refresh_session = RefreshSession(
        user_id=user_id,
        refresh_token_jti=jti,
        device_info=device_info,
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expires_days),
    )
    await refresh_repo.create(instance=refresh_session)
    await session.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

async def register_user(schema: RegisterRequest, session: AsyncSession) -> User:
    """Registers a new user account.

    Orchestration steps:
        1. Check if the email is already taken.
        2. Hash the plain-text password.
        3. Create the ``User`` ORM instance.
        4. Persist via ``UserRepository.create``.

    Args:
        schema: The validated registration request.
        session: The active database session.

    Returns:
        The newly created ``User`` ORM instance.

    Raises:
        UserAlreadyExistsException: If the email is already registered.
    """
    user_repo = UserRepository(session=session) # type: ignore

    # Step 1: Check email uniqueness
    is_user_exist = await user_repo.is_exist_by_email(schema.email)
    if is_user_exist:
        raise UserAlreadyExistsException(field='email', value=schema.email)

    # Step 2: Hash the password
    hashed_password = hash_password(password=schema.password)


    # Step 3: Build the ORM model
    instance = User(
        name=schema.name,
        email=schema.email,
        hashed_password=hashed_password,
    )

    # Step 4: Persist with IntegrityError safety net
    try:
        user = await user_repo.create(instance=instance)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise UserAlreadyExistsException(field='email', value=schema.email)
    
    return user


async def login_user(schema: LoginRequest, session: AsyncSession) -> TokenResponse:
    """Authenticates a user and issues a JWT access token.

    Orchestration steps:
        1. Fetch the user by email.
        2. Verify the password hash.
        3. Check that the user account is active.
        4. Generate and return the JWT access token.

    Args:
        schema: The validated login request containing email and password.
        session: The active database session.

    Returns:
        A ``TokenResponse`` containing the JWT ``access_token``.

    Raises:
        InvalidCredentialsException: If the email or password is wrong.
        UserInactiveException: If the user account is deactivated.
    """
    user_repo = UserRepository(session=session) # type: ignore

    # Step 1: Fetch user by email
    user = await user_repo.get_by_email(schema.email)
    if user is None:
        raise InvalidCredentialsException()

    # Step 2: Verify the password
    is_hashed_match = verify_password(
        password=schema.password,
        hashed_password=user.hashed_password,
    )
    if not is_hashed_match:
        raise InvalidCredentialsException()

    # Step 3: Verify the account is active
    if not user.is_active:
        raise UserInactiveException(identifier=str(user.id))

    # Step 4: Issue dual token pair
    return await _issue_token_pair(user_id=user.id, session=session)



async def logout(refresh_token_str: str, session: AsyncSession) -> None:
    """Revokes a single refresh session (logout current device).

    Args:
        refresh_token_str: The refresh token to revoke.
        session: The active database session.

    Raises:
        InvalidCredentialsException: If the token is malformed.
    """
    payload = decode_refresh_token(token=refresh_token_str)
    jti = payload.jti

    refresh_repo = RefreshSessionRepository(session=session) # type: ignore
    await refresh_repo.revoke_by_jti(jti=jti) # type: ignore


async def logout_all(user_id: int, session: AsyncSession) -> None:
    """Revokes all refresh sessions for a user (logout all devices).

    Args:
        user_id: The user's primary key.
        session: The active database session.
    """
    refresh_repo = RefreshSessionRepository(session=session) # type: ignore
    await refresh_repo.revoke_all_for_user(user_id=user_id)


async def refresh_token(schema: RefreshRequest, session: AsyncSession) -> TokenResponse:
    """Exchanges a valid refresh token for a new token pair (rotation).

    Rotation Protocol:
        1. Decode the refresh token to extract the JTI.
        2. Look up the refresh session in the database.
        3. Verify the session exists, is not revoked, and not expired.
        4. Revoke the old refresh session.
        5. Issue a fresh token pair.

    Args:
        schema: The request containing the current refresh token.
        session: The active database session.

    Returns:
        A new TokenResponse with fresh access + refresh tokens.

    Raises:
        InvalidCredentialsException: If the token is malformed or expired.
        TokenRevokedException: If the session is revoked or not found.
    """
    # Step 1: Decode the refresh token
    payload = decode_refresh_token(token=schema.refresh_token)
    user_id = int(payload.sub)
    jti = payload.jti

    # Step 2: Look up the session
    refresh_repo = RefreshSessionRepository(session=session) # type: ignore
    existing_session = await refresh_repo.get_by_jti(jti=jti) # type: ignore

    # Step 3: Validate the session
    if existing_session is None:
        raise TokenRevokedException()

    if existing_session.is_revoked:
        # Potential token theft — revoke all sessions for this user
        await refresh_repo.revoke_all_for_user(user_id=user_id)
        raise TokenRevokedException()

    expires_at = existing_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise TokenRevokedException()

    # Step 4: Revoke the old session (rotation)
    await refresh_repo.revoke_by_jti(jti=jti) # type: ignore

    # Step 5: Issue a fresh pair
    return await _issue_token_pair(user_id=user_id, session=session)