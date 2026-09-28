from collections.abc import AsyncGenerator
from typing import Callable, ParamSpec, TypeVar, Awaitable
import functools
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


from .engine import AsyncEngineLocal
from ..settings import settings


AsyncSessionLocal = async_sessionmaker(
    bind=AsyncEngineLocal,
    class_=AsyncSession,
    autoflush=settings.autoflush,
    expire_on_commit=settings.expire_on_commit
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise


_R = TypeVar('_R')
_P = ParamSpec('_P')

def inject_session(func: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
    @functools.wraps(func)
    async def wrapper(*args: _P.args, **kw: _P.kwargs) -> _R:
        async with AsyncSessionLocal() as session:
            try:
                if 'session' in kw:
                    kw['session'] = session
                result = await func(*args, **kw)
                await session.commit()
                return result
            except:
                await session.rollback()
                raise
            
    return wrapper