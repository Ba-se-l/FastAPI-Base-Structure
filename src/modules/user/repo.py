from typing import Literal, overload
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import BaseRepository

from .model import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(class_=User, session=session)


    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by_attr(email=email)


    @overload
    async def is_exist_by_email(
        self,
        email: str,
        return_orm: Literal[False] = False
    ) -> bool: ...
    
    @overload
    async def is_exist_by_email(
        self,
        email: str,
        return_orm: Literal[True]
    ) -> tuple[bool, User | None]: ...

    async def is_exist_by_email(
        self,
        email: str,
        return_orm: bool = False
    ) -> bool | tuple[bool, User | None]:
        user = await self.get_by_email(email)
        return user is not None, user if return_orm else user is not None


    async def is_active_by_id(self, id: int) -> bool:
        user = await self.get_by_id(id=id)
        return user.is_active if user is not None else False
