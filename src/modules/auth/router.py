from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.settings import settings
from src.database import get_session
from src.modules.user import User, UserResponse
from src.share import MessageResponse, AuditContext, get_audit_context
from .dependencies import get_current_user
from .schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
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
    audit_ctx: AuditContext = Depends(get_audit_context)
) -> UserResponse:
    """Registers a new user and returns the user profile."""
    user = await service.register_user(schema=request, session=session, audit_ctx=audit_ctx)

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
    audit_ctx: AuditContext = Depends(get_audit_context)
) -> TokenResponse:
    """Authenticates a user and issues a dual-token pair."""
    return await service.login_user(schema=request, session=session, audit_ctx=audit_ctx)


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
    audit_ctx: AuditContext = Depends(get_audit_context)
) -> TokenResponse:
    """Rotates refresh token and issues a fresh token pair."""
    return await service.refresh_token(schema=request, session=session, audit_ctx=audit_ctx)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout current device",
)
async def logout_endpoint(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
    audit_ctx: AuditContext = Depends(get_audit_context)
) -> MessageResponse:
    """Revokes the provided refresh token (single device logout)."""
    await service.logout(refresh_token_str=request.refresh_token, session=session, audit_ctx=audit_ctx)
    return MessageResponse(message="Logged out successfully.")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout all devices",
)
async def logout_all_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    audit_ctx: AuditContext = Depends(get_audit_context)
) -> MessageResponse:
    """Revokes all refresh sessions for the current user."""
    await service.logout_all(user_id=current_user.id, session=session, audit_ctx=audit_ctx)
    return MessageResponse(message="All sessions revoked successfully.")