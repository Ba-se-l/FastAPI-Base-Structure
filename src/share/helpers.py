from typing import Any
from sqlalchemy.orm import DeclarativeBase
from fastapi import Request
from fastapi.encoders import jsonable_encoder

from .schemas import AuditContext, AuditContextDict


def get_extra_dict_for_updates(
    *,
    update_dict: dict[str, Any],
    old_state: dict[str, Any] | DeclarativeBase | None = None
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


def get_audit_context(request: Request) -> AuditContext:
    """Extracts client IP, user agent, and request ID from the HTTP request.

    Args:
        request: The incoming FastAPI HTTP request.

    Returns:
        Immutable AuditContext data class populated from request headers and state.
    """
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
    else:
        ip = request.client.host if request.client else None

    ua = request.headers.get('user-agent')
    req_id = getattr(request.state, 'request_id', None)

    return AuditContext(
        ip_address=ip,
        user_agent=ua,
        request_id=req_id,
    )


def get_audit_context_dict(ctx: AuditContext | None = None) -> AuditContextDict:
    """Converts an AuditContext instance into a TypedDict representation.

    Args:
        ctx: Optional AuditContext instance.

    Returns:
        AuditContextDict with standardized keys (ip, ua, req_id).
    """
    return AuditContextDict(
        ip=ctx.ip_address if ctx else None,
        ua=ctx.user_agent if ctx else None,
        req_id=ctx.request_id if ctx else None,
    )