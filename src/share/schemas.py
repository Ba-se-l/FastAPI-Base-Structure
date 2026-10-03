from typing_extensions import TypedDict
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel as Base
from .enum import TokenType


_HTTP_ERROR_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}
    
class TokenPayload(Base):
    sub: str 
    type: TokenType
    jti: str | None = None
    iat: datetime
    exp: datetime


@dataclass(frozen=True, slots=True)
class AuditContext:
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


class AuditContextDict(TypedDict, total=True):
    ip: str | None
    """IP Address"""
    ua: str | None
    """User Agent"""
    req_id: str | None
    """Request ID"""


class TokenResponse(Base):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'