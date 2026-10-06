import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import DomainEvent


logger = logging.getLogger(__name__)


type EventHandler[E: DomainEvent] = Callable[[E, AsyncSession | None], Awaitable[None]]


class AsyncEventBus:
    """In-process publish/subscribe dispatcher for domain events.

    Handlers are executed sequentially in registration order. Sequential
    execution is mandatory because a shared ``AsyncSession`` is not safe
    for concurrent use.

    Attributes:
        _handlers: Mapping of concrete event type to its ordered handlers.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler[Any]]] = defaultdict(list)


    def subscribe[E: DomainEvent](
        self,
        event_type: type[E],
        handler: EventHandler[E]
    ) -> None:
        """Registers a handler for an exact event type (idempotent).

        Args:
            event_type: Concrete DomainEvent subclass to listen for.
            handler: Async callable receiving the event and an optional session.
        """
        handlers = self._handlers[event_type]
        if handler in handlers:
            return 
        handlers.append(handler)


    async def publish(
        self,
        event: DomainEvent,
        *,
        session: AsyncSession | None = None
    ) -> None:
        """Dispatches an event to all handlers registered for its exact type.

        Args:
            event: The immutable domain fact to broadcast.
            session: Optional active transaction made available to handlers.
                Handlers decide whether to use it or open an autonomous session.
        """
        for handler in self._handlers.get(type(event), ()):
            await self._run(handler, event, session)


    async def clear(self) -> None:
        """Removes every registered handler (used for test isolation)."""
        self._handlers.clear()


    async def _run(
        self,
        handler: EventHandler[Any],
        event: DomainEvent,
        session: AsyncSession | None
    ) -> None:
        """Executes a single handler, isolating and logging its failures.

        Args:
            handler: The handler to execute.
            event: The event being dispatched.
            session: Optional active transaction forwarded to the handler.
        """
        try: 
            await handler(event, session)
        except Exception as exc:
            logger.error(
                'Unhandled error in event handler [%s] for event [%s]: %s',
                getattr(handler, '__name__', repr(handler)),
                type(event).__name__,
                exc,
                exc_info=True,
            )


event_bus = AsyncEventBus()