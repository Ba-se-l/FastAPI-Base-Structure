import ipaddress
from typing import Any
from sqlalchemy.orm import DeclarativeBase
from fastapi import Request
from fastapi.encoders import jsonable_encoder

from src.settings import settings
from .limits import AUDIT_USER_AGENT_MAX
from .schemas import AuditContext, AuditContextDict


def _is_trusted_proxy(host: str) -> bool:
    """Returns True if host is inside any configured trusted proxy network."""
    if not settings.trusted_proxies:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    for net_str in settings.trusted_proxies:
        try:
            if ip in ipaddress.ip_network(net_str, strict=False):
                return True
        except ValueError:
            continue
    return False


def resolve_client_ip(request: Request) -> str | None:
    """Resolves the client IP, honouring X-Forwarded-For only from trusted proxies."""
    peer = request.client.host if request.client else None
    if not (settings.trust_proxy_headers and peer and _is_trusted_proxy(peer)):
        return peer
    chain = [p.strip() for p in request.headers.get('x-forwarded-for', '').split(',') if p.strip()]
    for raw in reversed(chain):
        try:
            ip = str(ipaddress.ip_address(raw))
        except ValueError:
            return peer  # malformed chain -> distrust entirely
        if not _is_trusted_proxy(ip):
            return ip
    return peer


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
    ip = resolve_client_ip(request)
    ua = request.headers.get('user-agent')
    if ua is not None:
        ua = ua[:AUDIT_USER_AGENT_MAX]

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