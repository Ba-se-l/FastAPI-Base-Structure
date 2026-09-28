from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status

from src.database import get_session
from src.settings import settings


from .schema import UserResponse
from . import service

router = APIRouter(prefix=f"{settings.api_prefix}/users", tags=["Authentication"])

