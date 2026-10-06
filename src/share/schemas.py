from typing_extensions import TypedDict
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


class TokenResponse(Base):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'

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


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Immutable base for every domain fact published on the event bus.

    Subclasses MUST be declared with ``kw_only=True`` so they can define
    required fields without violating dataclass default-ordering rules.
    """

    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """UTC timestamp at which the fact occurred."""

    audit_ctx: AuditContext | None = None
    """Request telemetry (IP, user agent, request ID) captured at publish time."""