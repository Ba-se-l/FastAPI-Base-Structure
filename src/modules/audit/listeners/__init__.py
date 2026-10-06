from src.share.event_bus import AsyncEventBus

from .auth import register_auth_listeners
from .user import register_user_listeners

__all__ = (
    'register_audit_listeners',
)


def register_audit_listeners(bus: AsyncEventBus) -> None:
    """Wires all audit listeners across all domain boundaries to the event bus.

    Args:
        bus: The application asynchronous event bus instance.
    """
    register_user_listeners(bus)
    register_auth_listeners(bus)
