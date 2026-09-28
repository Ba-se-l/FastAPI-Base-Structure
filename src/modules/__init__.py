from fastapi import APIRouter

from .audit import router as audit_router
from .auth import router as auth_router
from .user import router as user_router


api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(audit_router)


__all__ = (
    'api_router',
)