import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from hashlib import sha256


from ..exc import InvalidCredentialsException
from ..share.enum import TokenType
from ..share.schemas import TokenPayload
from ..settings import settings


def _utf8(seq: str) -> bytes:
    return seq.encode('utf-8')


def hash_password(password: str) -> str:

    sha256_hash = sha256(_utf8(password)).hexdigest()

    salt = bcrypt.gensalt()

    hashed_bytes = bcrypt.hashpw(_utf8(sha256_hash), salt)

    return hashed_bytes.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:

    sha256_hash = sha256(_utf8(password)).hexdigest()

    try:
        return bcrypt.checkpw(_utf8(sha256_hash), _utf8(hashed_password))
    except ValueError:
        return False




def create_access_token(user_id: int | uuid.UUID, expires_delta: timedelta | None = None) -> str:


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

    """
    Without exclude_none=True :
    ```bash
    raise InvalidJTIError("JWT ID must be a string")
    jwt.exceptions.InvalidJTIError: JWT ID must be a string
    ```
    """
    return jwt.encode(payload.model_dump(exclude_none=True), key=settings.access_secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: int | uuid.UUID, jti: str | None = None) -> tuple[str, str]:

    if jti is None:
        jti = uuid.uuid4().hex

    now = datetime.now(timezone.utc)
    expires_delta = timedelta(days=settings.refresh_token_expires_days)

    payload = TokenPayload(
        sub=str(user_id),
        type=TokenType.REFRESH,
        jti=jti,
        iat=now,
        exp=now + expires_delta
    )

    return jwt.encode(payload.model_dump(), key=settings.refresh_secret_key, algorithm=settings.algorithm), jti



def decode_access_token(token: str) -> TokenPayload:

    try:
        payload = TokenPayload.model_validate(
            jwt.decode(
                jwt=token,
                key=settings.access_secret_key,
                algorithms=[settings.algorithm]
            )
        )

        if payload.type != TokenType.ACCESS:
            raise InvalidCredentialsException()

        return payload
    
    except jwt.PyJWTError:
        raise InvalidCredentialsException()

def decode_refresh_token(token: str) -> TokenPayload:

    try:
        payload = TokenPayload.model_validate(
            jwt.decode(
                jwt=token,
                key=settings.refresh_secret_key,
                algorithms=[settings.algorithm]
            )
        )

        if payload.jti is None:
            raise InvalidCredentialsException()

        if payload.type != TokenType.REFRESH:
            raise InvalidCredentialsException()

        return payload

    except jwt.PyJWTError:
        raise InvalidCredentialsException()
    