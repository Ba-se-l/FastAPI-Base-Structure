import logging
from datetime import datetime, timezone
from typing import Generic, TypeVar, Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseModel

_O = TypeVar('_O', bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[_O]):
    """Concrete generic base repository providing default CRUD operations.

    Subclasses inherit all methods and may override them for
    domain-specific behavior. Repositories NEVER call ``commit()``
    or ``rollback()`` — the transaction boundary is owned by the
    caller (service layer or the ``get_session`` FastAPI dependency).

    Args:
        class_: The SQLAlchemy ORM model class this repository manages.
        session: The active async database session.
    """

    def __init__(self, class_: type[_O], session: AsyncSession):
        self.model = class_
        self.session = session

    async def get_by_id(self, id: UUID | int) -> _O | None:
        """Fetches a single record by its primary key.

        Args:
            id: The primary key value (UUID or integer).

        Returns:
            The ORM instance or ``None`` if not found.
        """
        return await self.session.get(self.model, id)

    async def get_by_attr(self, **kw: Any) -> _O | None:
        """Fetches a single record matching the given attribute filters.

        Args:
            **kw: Column name/value pairs to filter by.

        Returns:
            The ORM instance or ``None`` if not found.
        """
        result = await self.session.execute(
            select(self.model).filter_by(**kw)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[_O], int]:
        """Fetches a paginated list of records with total count.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A tuple of ``(list_of_items, total_count)``.
        """
        # Count query
        count_result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        total = count_result.scalar_one()

        # Data query with deterministic order by primary key/identifier
        stmt = select(self.model)
        if hasattr(self.model, "id"):
            stmt = stmt.order_by(self.model.id)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create(self, instance: _O) -> _O:
        """Adds a new ORM instance to the session.

        Args:
            instance: The ORM model instance to persist.

        Returns:
            The same instance (now tracked by the session).
        """
        self.session.add(instance)
        return instance

    async def update(self, instance: _O, update_dict: dict[str, Any]) -> _O:
        """Applies a dictionary of updates to an existing ORM instance.

        Automatically sets ``updated_at`` if the model has that attribute
        and it is not already included in the update payload.

        Args:
            instance: The ORM instance to update.
            update_dict: Key-value pairs of attributes to set.

        Returns:
            The updated ORM instance.
        """
        if hasattr(instance, 'updated_at'):
            if 'updated_at' not in update_dict:
                update_dict['updated_at'] = datetime.now(timezone.utc)

        for k, v in update_dict.items():
            setattr(instance, k, v)

        self.session.add(instance)
        return instance

    async def delete(self, instance: _O) -> bool:
        """Removes an ORM instance from the session.

        Args:
            instance: The ORM instance to delete.

        Returns:
            ``True`` if the delete was staged successfully.

        Raises:
            Exception: Re-raises any database-level error after logging.
        """
        try:
            await self.session.delete(instance)
            return True
        except Exception:
            logger.exception(
                "Failed to delete %s(id=%s)",
                type(instance).__name__,
                getattr(instance, 'id', '?'),
            )
            raise