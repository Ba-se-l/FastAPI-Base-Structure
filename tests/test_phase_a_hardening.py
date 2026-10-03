from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import BaseRepository
from src.modules.audit.model import AuditLog
from src.modules.audit.repo import AuditLogRepository
from src.modules.auth.model import RefreshSession
from src.modules.auth.repo import RefreshSessionRepository
from src.modules.user.model import User
from src.modules.user.repo import UserRepository
from src.security import SECURITY_PASSWORD_HASH, hash_password


@pytest.mark.asyncio
async def test_audit_log_immutability(db_session: AsyncSession):
    """Verifies that AuditLogRepository strictly blocks updates and deletions."""
    repo = AuditLogRepository(session=db_session)
    log_entry = AuditLog(
        event_type="TEST_IMMUTABLE",
        severity="INFO",
        message="Original immutable audit record",
    )
    saved = await repo.create(log_entry)
    await db_session.flush()

    # Verify update is strictly prohibited
    with pytest.raises(NotImplementedError) as update_err:
        await repo.update(saved, {"message": "Tampered message"})
    assert "immutable" in str(update_err.value).lower()

    # Verify delete is strictly prohibited
    with pytest.raises(NotImplementedError) as delete_err:
        await repo.delete(saved)
    assert "immutable" in str(delete_err.value).lower()


@pytest.mark.asyncio
async def test_refresh_token_cas_atomic_revocation(db_session: AsyncSession):
    """Verifies atomic Compare-And-Swap (CAS) revocation behavior."""
    user_repo = UserRepository(session=db_session)
    user = User(
        name="CAS Test User",
        email="cas.test@enterprise.io",
        hashed_password=hash_password("Pass12345!"),
    )
    user = await user_repo.create(user)
    await db_session.flush()

    refresh_repo = RefreshSessionRepository(session=db_session)
    session_instance = RefreshSession(
        user_id=user.id,
        refresh_token_jti="unique-cas-jti-001",
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await refresh_repo.create(session_instance)
    await db_session.flush()

    # First revocation should succeed (active -> revoked)
    first_attempt = await refresh_repo.revoke_if_active("unique-cas-jti-001")
    assert first_attempt is True

    # Second concurrent or duplicate revocation attempt MUST return False (CAS guard)
    second_attempt = await refresh_repo.revoke_if_active("unique-cas-jti-001")
    assert second_attempt is False

    # Non-existent JTI must also return False
    ghost_attempt = await refresh_repo.revoke_if_active("non-existent-jti")
    assert ghost_attempt is False


@pytest.mark.asyncio
async def test_deterministic_pagination_ordering(db_session: AsyncSession):
    """Verifies that BaseRepository.get_multi applies deterministic ordering by ID."""
    user_repo = UserRepository(session=db_session)

    created_ids: list[int] = []
    for idx in range(5):
        user = User(
            name=f"Order User {idx}",
            email=f"order_{idx}@enterprise.io",
            hashed_password=hash_password("Pass12345!"),
        )
        saved = await user_repo.create(user)
        await db_session.flush()
        created_ids.append(saved.id)

    items, total = await user_repo.get_multi(offset=0, limit=10)
    returned_ids = [item.id for item in items if item.id in created_ids]

    # Verify deterministic monotonic ascending order
    assert returned_ids == sorted(created_ids)


@pytest.mark.asyncio
async def test_login_timing_mitigation_invoked(client: AsyncClient):
    """Verifies that nonexistent email triggers dummy argon2 hash verification."""
    with patch("src.modules.auth.service.verify_password") as mock_verify:
        mock_verify.return_value = False

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent.user.probe@enterprise.io", "password": "SecretPassword123!"},
        )

        assert response.status_code == 401
        # verify_password MUST have been called with SECURITY_PASSWORD_HASH to prevent timing side-channel
        mock_verify.assert_called_once_with(
            "SecretPassword123!",
            SECURITY_PASSWORD_HASH,
        )
