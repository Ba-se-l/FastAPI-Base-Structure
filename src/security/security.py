import uuid
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash


from ..exc import InvalidCredentialsException
from ..share.enum import TokenType
from ..share.schemas import TokenPayload
from ..settings import settings

ctx = PasswordHash.recommended()

SECURITY_PASSWORD_HASH: str = ctx.hash("anti-timing-dummy-secret-fixed-entropy")
"""Pre-computed dummy argon2 hash constant used to equalize response latency during invalid login attempts."""


def hash_password(password: str) -> str:
    """Hashes a plaintext password using the recommended Argon2 password hasher.

    Args:
        password: The plaintext password string to hash.

    Returns:
        The encoded Argon2 password hash string.
    """
    return ctx.hash(password=password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2 password hash.

    Args:
        password: The plaintext password string to verify.
        hashed_password: The existing Argon2 hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return ctx.verify(password=password, hash=hashed_password)


def create_access_token(user_id: int | uuid.UUID, expires_delta: timedelta | None = None) -> str:
    """Generates a signed JWT access token for authentication.

    Args:
        user_id: The authenticated user's unique primary identifier.
        expires_delta: Optional custom duration before expiration. Defaults to settings value.

    Returns:
        A signed JWT access token string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expires_minutes)

    now = datetime.now(timezone.utc)

    payload = TokenPayload(
        sub=str(user_id),
        type=TokenType.ACCESS,
        jti=uuid.uuid4().hex,
        iat=now,
        exp=now + expires_delta,
    )

    return jwt.encode(
        payload.model_dump(exclude_none=True),
        key=settings.access_secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(user_id: int | uuid.UUID, jti: str | None = None) -> tuple[str, str]:
    """Generates a signed JWT refresh token with an assigned unique JTI identifier.

    Args:
        user_id: The authenticated user's unique primary identifier.
        jti: Optional pre-assigned JWT ID string. If None, a random UUID hex is generated.

    Returns:
        A tuple of (encoded_jwt_refresh_token, jti_identifier).
    """
    if jti is None:
        jti = uuid.uuid4().hex

    now = datetime.now(timezone.utc)
    expires_delta = timedelta(days=settings.refresh_token_expires_days)

    payload = TokenPayload(
        sub=str(user_id),
        type=TokenType.REFRESH,
        jti=jti,
        iat=now,
        exp=now + expires_delta,
    )

    token = jwt.encode(
        payload.model_dump(),
        key=settings.refresh_secret_key,
        algorithm=settings.algorithm,
    )
    return token, jti


def decode_access_token(token: str) -> TokenPayload:
    """Decodes and validates a signed JWT access token.

    Args:
        token: The raw encoded JWT access token string.

    Returns:
        The validated TokenPayload schema.

    Raises:
        InvalidCredentialsException: If the token signature is invalid, expired, or not an ACCESS token.
    """
    try:
        payload = TokenPayload.model_validate(
            jwt.decode(
                jwt=token,
                key=settings.access_secret_key,
                algorithms=[settings.algorithm],
            )
        )

        if payload.type != TokenType.ACCESS:
            raise InvalidCredentialsException()

        return payload

    except jwt.PyJWTError as exc:
        raise InvalidCredentialsException() from exc


def decode_refresh_token(token: str) -> TokenPayload:
    """Decodes and validates a signed JWT refresh token.

    Args:
        token: The raw encoded JWT refresh token string.

    Returns:
        The validated TokenPayload schema containing the JTI.

    Raises:
        InvalidCredentialsException: If the token signature is invalid, expired, lacks JTI, or not REFRESH.
    """
    try:
        payload = TokenPayload.model_validate(
            jwt.decode(
                jwt=token,
                key=settings.refresh_secret_key,
                algorithms=[settings.algorithm],
            )
        )

        if payload.jti is None:
            raise InvalidCredentialsException()

        if payload.type != TokenType.REFRESH:
            raise InvalidCredentialsException()

        return payload

    except jwt.PyJWTError as exc:
        raise InvalidCredentialsException() from exc
    