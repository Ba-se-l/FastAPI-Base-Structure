from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import BaseRepository
from .model import RefreshSession

def now()-> datetime:
    return datetime.now(timezone.utc)

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


    async def revoke_if_active(self, jti: str) -> bool:
        """Atomically revokes a refresh session only if it is currently active.

        This guarantees atomic Compare-And-Swap (CAS) semantics to prevent
        race conditions where two concurrent requests rotate the same token.

        Args:
            jti: The JWT ID string to revoke.

        Returns:
            True if the session was successfully revoked (affected rows > 0),
            False if it was already revoked or not found.
        """

        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.refresh_token_jti == jti,
                RefreshSession.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now())
        )

        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0


    async def revoke_by_jti(self, jti: str) -> None:
        """Revokes a single refresh session by JTI.

        Args:
            jti: The JWT ID string to revoke.
        """
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.refresh_token_jti == jti)
            .values(is_revoked=True, revoked_at=now())
        )
        await self.session.execute(stmt)


    async def revoke_family(self, family_id: str) -> int:
        """Revokes all active refresh sessions belonging to a specific lineage family.

        Used for targeted device isolation when token replay or device logout occurs.

        Args:
            family_id: The lineage family identifier string.

        Returns:
            The number of revoked session records.
        """
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def revoke_all_for_user(self, user_id: int) -> int:
        """Revokes all active refresh sessions for a user.

        Used for logout-all-devices and post-password-change invalidation.

        Args:
            user_id: The user's primary key.

        Returns:
            The number of revoked session records.
        """
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def is_family_active(self, family_id: str, user_id: int) -> bool:
        """Checks whether a session family currently possesses at least one valid, unrevoked token.

        Used by authentication guards to verify device session validity.

        Args:
            family_id: The session family identifier.
            user_id: The expected user subject ID.

        Returns:
            True if the family has an active, unexpired session; False otherwise.
        """
        stmt = (
            select(RefreshSession.id)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.user_id == user_id,
                RefreshSession.is_revoked.is_(False),
                RefreshSession.expires_at > now(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_active_for_user(self, user_id: int) -> Sequence[RefreshSession]:
        """Fetches all active, unrevoked sessions for a specific user.

        Args:
            user_id: The user's primary key.

        Returns:
            A sequence of active RefreshSession instances.
        """
        stmt = (
            select(RefreshSession)
            .where(
                RefreshSession.user_id == user_id,
                RefreshSession.is_revoked.is_(False),
                RefreshSession.expires_at > now(),
            )
            .order_by(RefreshSession.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


