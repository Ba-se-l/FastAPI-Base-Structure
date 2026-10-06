from sqlalchemy.ext.asyncio import AsyncSession

from src.exc import AccessDeniedException
from src.share import AuditContext, Roles, UserAction, get_extra_dict_for_updates, event_bus

from .events import (
    UserAccessDenied,
    UserDeactivated,
    UserInactiveTargeted,
    UserNotFound,
    UserUpdated,
    UserUpdateSkipped,
)
from .exc import UserInactiveException, UserNotFoundException
from .model import User
from .repo import UserRepository
from .schemas import UserUpdate


async def _get_user_by_id(
    user_id: int,
    session: AsyncSession,
    ctx: AuditContext | None = None,
) -> User:
    """Internal helper to fetch a user entity by ID without permission checks.

    Args:
        user_id: Integer primary key of the target user.
        session: Active async database session.
        ctx: Optional audit context.

    Returns:
        The matched User ORM entity.

    Raises:
        UserNotFoundException: If no user exists with the given ID.
    """
    user_repo = UserRepository(session=session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        await event_bus.publish(event=UserNotFound(audit_ctx=ctx, user_id=user_id))
        raise UserNotFoundException(identifier=str(user_id))

    return user


async def get_user_by_id(
    getter: User,
    user_id: int,
    session: AsyncSession,
    audit_ctx: AuditContext | None = None,
) -> User:
    """Retrieves a single user with authorization enforcement (Self or Admin only).

    Args:
        getter: The authenticated user requesting the profile.
        user_id: Target user ID to retrieve.
        session: Active async database session.
        audit_ctx: Optional audit context.

    Returns:
        The target User ORM entity.

    Raises:
        AccessDeniedException: If getter lacks permission.
        UserNotFoundException: If user does not exist.
    """
    # Security Rule: Authorize BEFORE querying to prevent User Enumeration attacks
    if getter.role != Roles.ADMIN and getter.id != user_id:
        await event_bus.publish(
            event=UserAccessDenied(
                audit_ctx=audit_ctx,
                actor_id=getter.id,
                actor_name=getter.name,
                target_user_id=user_id,
                action=UserAction.VIEW,
            )
        )
        raise AccessDeniedException('You are not authorized to view this profile.')

    return await _get_user_by_id(user_id=user_id, session=session, ctx=audit_ctx)


async def list_users(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    """Retrieves a paginated list of users and the total count.

    Args:
        session: Active async database session.
        offset: Number of records to skip.
        limit: Maximum number of records to retrieve.

    Returns:
        A tuple of (users_list, total_count).
    """
    user_repo = UserRepository(session=session)
    return await user_repo.get_multi(offset=offset, limit=limit)


async def update_user(
    updater: User,
    user_id: int,
    schema: UserUpdate,
    session: AsyncSession,
    audit_ctx: AuditContext | None = None,
) -> User:
    """Updates user profile attributes with strict RBAC checks and state audit trail.

    Args:
        updater: The user performing the modification.
        user_id: Integer primary key of the target user.
        schema: Validated fields to update.
        session: Active async database session.
        audit_ctx: Optional audit context.

    Returns:
        The updated User ORM entity.

    Raises:
        AccessDeniedException: If updater is not Admin and not modifying self, or attempting role escalation.
        UserNotFoundException: If no user exists with the given ID.
        UserInactiveException: If target user account is deactivated.
    """
    # 1. Authorize: Only Admin or Self can modify
    if updater.role != Roles.ADMIN and updater.id != user_id:
        await event_bus.publish(
            event=UserAccessDenied(
                audit_ctx=audit_ctx,
                actor_id=updater.id,
                actor_name=updater.name,
                target_user_id=user_id,
                action=UserAction.MODIFY,
            )
        )
        raise AccessDeniedException('You are not authorized to modify this user.')

    # 2. Authorize: Role escalation restriction
    if schema.role is not None and updater.role != Roles.ADMIN:
        await event_bus.publish(
            event=UserAccessDenied(
                audit_ctx=audit_ctx,
                actor_id=updater.id,
                actor_name=updater.name,
                target_user_id=user_id,
                action=UserAction.CHANGE_ROLE,
            )
        )
        raise AccessDeniedException('Only Administrators can modify user roles.')

    # 3. Retrieve target user
    user = await _get_user_by_id(user_id=user_id, session=session, ctx=audit_ctx)
    user_repo = UserRepository(session=session)

    # 3.5 Verify user is active
    if not user.is_active:
        await event_bus.publish(
            event=UserInactiveTargeted(
                audit_ctx=audit_ctx,
                actor_id=updater.id,
                actor_name=updater.name,
                target_user_id=user_id,
                action=UserAction.MODIFY,
            )
        )
        raise UserInactiveException(identifier=str(user_id))

    # 4. Apply updates with pre-update snapshot
    update_dict = schema.model_dump(exclude_unset=True)
    if update_dict:
        old_state = {k: getattr(user, k, None) for k in update_dict}
        user = await user_repo.update(instance=user, update_dict=update_dict)
        await session.flush()

        await event_bus.publish(
            event=UserUpdated(
                audit_ctx=audit_ctx,
                user_id=user_id,
                changes=get_extra_dict_for_updates(update_dict=update_dict, old_state=old_state),
            ),
            session=session,
        )
        return user

    await event_bus.publish(
        event=UserUpdateSkipped(
            audit_ctx=audit_ctx,
            user_id=user_id,
        )
    )
    return user


async def deactivate_user(
    user_id: int,
    session: AsyncSession,
    audit_ctx: AuditContext | None = None,
) -> User:
    """Deactivates a user account (soft deactivation).

    Args:
        user_id: Integer primary key of the user to deactivate.
        session: Active async database session.
        audit_ctx: Optional audit context.

    Returns:
        The deactivated User entity.

    Raises:
        UserNotFoundException: If the user does not exist.
    """
    user = await _get_user_by_id(user_id=user_id, session=session, ctx=audit_ctx)
    user_repo = UserRepository(session=session)
    user = await user_repo.update(instance=user, update_dict={'is_active': False})
    await session.flush()

    await event_bus.publish(
        event=UserDeactivated(
            audit_ctx=audit_ctx,
            user_id=user_id,
        ),
        session=session,
    )

    return user
