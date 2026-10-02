from typing_extensions import TypedDict
from typing import Any
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel as Base
from sqlalchemy.orm import DeclarativeBase
from fastapi import Request
from fastapi.encoders import jsonable_encoder

from .enum import TokenType

def get_extra_dict_for_updates( 
    *,
    update_dict: dict[str, Any],
    old_state: dict[str, Any] | DeclarativeBase | None = None,
) -> dict[str, dict[str, Any]]:
    """Builds a structured dictionary tracking old vs new values for audit logging.

    Args:
        update_dict: Dictionary of modified fields and their new values.
        old_state: Pre-update state as either a dictionary or ORM model snapshot taken before update.

    Returns:
        Structured diff dictionary: {field: {"old": ..., "new": ...}}.
    """
    if not update_dict:
        return {"update_dict": {}}

    old_map: dict[str, Any] = {}
    if isinstance(old_state, dict):
        old_map = old_state
    elif old_state is not None:
        old_map = {k: getattr(old_state, k, None) for k in update_dict}

    diff = {
        k: {"old": old_map.get(k), "new": v}
        for k, v in update_dict.items()
    }
    return jsonable_encoder(diff)

    



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



def get_audit_context(request: Request) -> AuditContext:

    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        client_ip = forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.client.host if request.client else None

    user_agent = request.headers.get('user-agent')
    request_id = getattr(request.state, 'request_id', None)

    return AuditContext(
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )
    

def get_audit_context_dict(ctx: AuditContext | None = None) -> AuditContextDict:
    return AuditContextDict(
        ip= ctx.ip_address if ctx else None,
        ua=ctx.user_agent if ctx else None,
        req_id=ctx.request_id if ctx else None
    )


class TokenResponse(Base):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'