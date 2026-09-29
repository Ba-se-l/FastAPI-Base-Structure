from sqlalchemy.ext.asyncio import AsyncSession

from .exc import UserNotFoundException
from .model import User
from .repo import UserRepository
from .schemas import UserUpdate


async def get_user_by_id(user_id: int, session: AsyncSession) -> User:
    """Fetches a single user by primary key ID.

    Args:
        user_id: Integer primary key of the target user.
        session: Active async database session.

    Returns:
        The matched User ORM entity.

    Raises:
        UserNotFoundException: If no user exists with the given ID.
    """
    user_repo = UserRepository(session=session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise UserNotFoundException(identifier=str(user_id))
    return user


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
    user_id: int,
    schema: UserUpdate,
    session: AsyncSession,
) -> User:
    """Updates user profile attributes.

    Args:
        user_id: Integer primary key of the target user.
        schema: Validated fields to update.
        session: Active async database session.

    Returns:
        The updated User ORM entity.

    Raises:
        UserNotFoundException: If no user exists with the given ID.
    """
    user = await get_user_by_id(user_id=user_id, session=session)
    user_repo = UserRepository(session=session)

    update_data = schema.model_dump(exclude_unset=True)
    if update_data:
        user = await user_repo.update(instance=user, update_dict=update_data)
        await session.flush()

    return user


async def deactivate_user(user_id: int, session: AsyncSession) -> User:
    """Deactivates a user account (soft deactivation).

    Args:
        user_id: Integer primary key of the user to deactivate.
        session: Active async database session.

    Returns:
        The deactivated User entity.

    Raises:
        UserNotFoundException: If the user does not exist.
    """
    user = await get_user_by_id(user_id=user_id, session=session)
    user_repo = UserRepository(session=session)
    user = await user_repo.update(instance=user, update_dict={'is_active': False})
    await session.flush()
    return user
