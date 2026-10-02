from sqlalchemy.ext.asyncio import AsyncSession

from src.share import Roles, AuditContext, get_extra_dict_for_updates
from src.modules.audit import save_success_event, save_failed_event, LogAction, LogSeverity
from src.exc import AccessDeniedException

from .exc import UserNotFoundException
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
        await save_failed_event(
            message=f"User with identifier ID [{user_id}] was not found.",
            session=session,
            event_type='USER_NOT_FOUND',
            severity=LogSeverity.ERROR,
            user_id=str(user_id),
            ctx=ctx,
        )
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
        await save_failed_event(
            message=(
                f"User [ID: {getter.id} | Name: {getter.name}] is not authorized "
                f"to view User [ID: {user_id}] profile."
            ),
            session=session,
            event_type=LogAction.SECURITY_ACCESS_DENIED,
            severity=LogSeverity.WARNING,
            user_id=str(getter.id),
            ctx=audit_ctx,
        )
        raise AccessDeniedException("You are not authorized to view this profile.")

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
    """
    # 1. Authorize: Only Admin or Self can modify
    if updater.role != Roles.ADMIN and updater.id != user_id:
        await save_failed_event(
            message=(
                f"User [ID: {updater.id} | Name: {updater.name}] is not authorized "
                f"to modify User [ID: {user_id}]."
            ),
            session=session,
            event_type=LogAction.SECURITY_ACCESS_DENIED,
            severity=LogSeverity.CRITICAL,
            user_id=str(updater.id),
            ctx=audit_ctx,
        )
        raise AccessDeniedException("You are not authorized to modify this user.")

    # 2. Authorize: Role escalation restriction
    if schema.role is not None and updater.role != Roles.ADMIN:
        await save_failed_event(
            message=(
                f"User [ID: {updater.id} | Name: {updater.name}] is not authorized "
                f"to modify user role for User [ID: {user_id}]."
            ),
            session=session,
            event_type=LogAction.SECURITY_ACCESS_DENIED,
            severity=LogSeverity.CRITICAL,
            user_id=str(updater.id),
            ctx=audit_ctx,
        )
        raise AccessDeniedException("Only Administrators can modify user roles.")

    # 3. Retrieve target user
    user = await _get_user_by_id(user_id=user_id, session=session, ctx=audit_ctx)
    user_repo = UserRepository(session=session)

    # 4. Apply updates with pre-update snapshot
    update_dict = schema.model_dump(exclude_unset=True)
    if update_dict:
        old_state = {k: getattr(user, k, None) for k in update_dict}
        user = await user_repo.update(instance=user, update_dict=update_dict)
        await session.flush()

        await save_success_event(
            message=f"User profile for ID [{user_id}] updated successfully.",
            session=session,
            event_type=LogAction.USER_UPDATED,
            user_id=str(user_id),
            ctx=audit_ctx,
            extra_data=get_extra_dict_for_updates(update_dict=update_dict, old_state=old_state),
        )
        return user
    else:
        await save_failed_event(
            message=f"Update skipped for user ID [{user_id}]; update dict was empty.",
            session=session,
            event_type=LogAction.USER_UPDATED,
            severity=LogSeverity.WARNING,
            user_id=str(user_id),
            ctx=audit_ctx,
            extra_data=get_extra_dict_for_updates(update_dict={}),
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

    await save_success_event(
        message=f"User account deactivated successfully [ID: {user_id}].",
        session=session,
        event_type=LogAction.USER_DEACTIVATED,
        user_id=str(user_id),
        ctx=audit_ctx,
        extra_data={'is_active': {'old': True, 'new': False}},
    )

    return user
