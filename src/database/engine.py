from sqlalchemy.ext.asyncio import create_async_engine

from .base import BaseModel
from ..settings import settings

AsyncEngineLocal = create_async_engine(
    url=settings.database_url,
    echo=settings.echo
)

async def create_all_tables() -> None:

    # from all.modules import sql.model.here
    # . . . 

    async with AsyncEngineLocal.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

