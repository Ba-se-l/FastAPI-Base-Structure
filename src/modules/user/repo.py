from sqlalchemy.ext.asyncio import AsyncSession
from src.database import BaseRepository

from .model import User

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(class_=User, session=session)


    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by_attr(email=email)

    async def is_exist_by_email(self, email: str) -> bool:
        return await self.get_by_email(email) is not None



