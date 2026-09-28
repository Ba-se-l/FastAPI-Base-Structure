from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseModel

_O = TypeVar('_O', bound=BaseModel)


class BaseRepository(ABC, Generic[_O]):
    def __init__(self, class_: type[_O], session: AsyncSession):
        self.model = class_
        self.session = session

    @abstractmethod
    async def get_by_id(self, id: UUID | int) -> _O | None:
        return await self.session.get(self.model, id)

    @abstractmethod
    async def get_by_attr(self, **kw) -> _O | None:
        result = await self.session.execute(
            select(self.model)
            .filter_by(**kw)
        )
        return result.scalar_one_or_none()

    @abstractmethod
    async def create(self, instance: _O) -> _O:
        self.session.add(instance)
        return instance

    @abstractmethod
    async def update(self, instance: _O, update_dict: dict[str, Any]) -> _O:

        if hasattr(instance, 'updated_at'):
            if 'updated_at' not in update_dict:
                from datetime import datetime, timezone
                update_dict['updated_at'] = datetime.now(timezone.utc)

        for k, v in update_dict.items():
            setattr(instance, k, v)

        self.session.add(isinstance)
        return instance

    @abstractmethod
    async def delete(self, instance: _O) -> bool:
        try:
            await self.session.delete(instance)
            return True
        except:
            return False