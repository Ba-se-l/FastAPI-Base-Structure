from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import BaseRepository
from .model import RefreshSession



class RefreshSessionRepository(BaseRepository[RefreshSession]):
    """Repository for RefreshSession CRUD and revocation operations.

    Attributes:
        model: The RefreshSession ORM class.
        session: The active async database session.
    """

    def __init__(self, session: AsyncSession):
        """Initializes with the RefreshSession model.

        Args:
            session: The active async database session.
        """
        super().__init__(class_=RefreshSession, session=session)

    async def get_by_jti(self, jti: str) -> RefreshSession | None:
        """Fetches a refresh session by its unique JTI claim.

        Args:
            jti: The JWT ID string.

        Returns:
            The RefreshSession instance or None if not found.
        """
        return await self.get_by_attr(refresh_token_jti=jti)

    async def revoke_by_jti(self, jti: str) -> None:
        """Revokes a single refresh session by JTI.

        Args:
            jti: The JWT ID string to revoke.
        """
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.refresh_token_jti == jti)
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)

    async def revoke_all_for_user(self, user_id: int) -> None:
        """Revokes all active refresh sessions for a user.

        Used for logout-all-devices and post-password-change invalidation.

        Args:
            user_id: The user's primary key.
        """
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)


