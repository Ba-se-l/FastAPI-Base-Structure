from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.exc import AccessDeniedException
from src.modules.auth.dependencies import get_current_user, require_role
from src.settings import settings
from src.share import (
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    Roles,
)
from . import service
from .model import User
from .schemas import UserResponse, UserUpdate

router = APIRouter(prefix=f"{settings.api_prefix}/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile information of the currently authenticated user.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Returns the authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all users (Admin only)",
    description="Returns a paginated list of all registered users with metadata.",
)
async def list_users_endpoint(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_role(Roles.ADMIN)),
) -> PaginatedResponse[UserResponse]:
    """Retrieves a paginated list of users."""
    users, total = await service.list_users(
        session=session,
        offset=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse(
        data=[UserResponse.model_validate(u) for u in users],
        pagination=PaginationMeta.from_params(
            page=pagination.page,
            page_size=pagination.page_size,
            total=total,
        ),
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieves a user by primary key. Restricted to Admin or the user themselves.",
)
async def get_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Retrieves user by ID with authorization check."""
    if current_user.role != Roles.ADMIN and current_user.id != user_id:
        raise AccessDeniedException("You are not authorized to view this user profile.")

    user = await service.get_user_by_id(user_id=user_id, session=session)
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Updates user fields. Role updates are restricted to Admins.",
)
async def update_user_endpoint(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Updates user information with privilege checks."""
    if current_user.role != Roles.ADMIN and current_user.id != user_id:
        raise AccessDeniedException("You are not authorized to modify this user.")

    # Restrict role escalation: only admins can change role
    if request.role is not None and current_user.role != Roles.ADMIN:
        raise AccessDeniedException("Only administrators can modify user roles.")

    updated_user = await service.update_user(
        user_id=user_id,
        schema=request,
        session=session,
    )
    return UserResponse.model_validate(updated_user)
