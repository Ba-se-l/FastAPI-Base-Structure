from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.settings import settings
from src.database import get_session
from src.modules.user import User, UserResponse
from .dependencies import get_current_user
from .schemas import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from . import service

router = APIRouter(prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with a hashed password.",
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Registers a new user and returns the user profile."""
    user = await service.register_user(schema=request, session=session)
    
    return UserResponse.model_validate(user)

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and get token pair",
    description="Authenticates user credentials and returns JWT access + refresh tokens.",
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticates a user and issues a dual-token pair."""
    return await service.login_user(schema=request, session=session)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh token pair",
    description=(
        "Exchanges a valid refresh token for a new access + refresh token pair. "
        "The old refresh token is revoked (rotation)."
    ),
)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Rotates refresh token and issues a fresh token pair."""
    return await service.refresh_token(schema=request, session=session)



@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout current device",
)
async def logout_endpoint(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Revokes the provided refresh token (single device logout)."""
    await service.logout(refresh_token_str=request.refresh_token, session=session)
    return {"message": "Logged out successfully."}


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Logout all devices",
)
async def logout_all_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Revokes all refresh sessions for the current user."""
    await service.logout_all(user_id=current_user.id, session=session)
    return {"message": "All sessions revoked successfully."}