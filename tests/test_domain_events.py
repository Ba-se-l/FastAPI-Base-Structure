import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.audit.enum import LogAction
from src.modules.audit.repo import AuditLogRepository
from src.modules.auth.events import (
    AuthAction,
    AuthAllSessionsRevoked,
    AuthEmailAlreadyRegistered,
    AuthEmailNotFound,
    AuthInactiveUserRejected,
    AuthInvalidPassword,
    AuthLoggedIn,
    AuthLoggedOut,
    AuthRefreshSessionExpired,
    AuthRefreshSessionNotFound,
    AuthRegistrationFailed,
    AuthTokenPairIssued,
    AuthTokenReplayDetected,
    AuthTokenRotated,
    AuthUserRegistered,
)
from src.modules.user.events import (
    UserAccessDenied,
    UserDeactivated,
    UserInactiveTargeted,
    UserNotFound,
    UserUpdated,
    UserUpdateSkipped,
)
from src.share import AuditContext, UserAction
from src.share.event_bus import AsyncEventBus, DomainEvent, event_bus


@pytest.mark.asyncio
async def test_user_domain_events_dispatch(db_session: AsyncSession) -> None:
    """Verifies that every User domain event properly creates an audit log entry."""
    audit_repo = AuditLogRepository(session=db_session)
    ctx = AuditContext(ip_address="127.0.0.1", user_agent="PyTestClient", request_id="req-user-1")

    # 1. UserNotFound
    await event_bus.publish(UserNotFound(audit_ctx=ctx, user_id=999))

    # 2. UserAccessDenied
    await event_bus.publish(
        UserAccessDenied(
            audit_ctx=ctx,
            actor_id=1,
            actor_name="Attacker",
            target_user_id=2,
            action=UserAction.VIEW,
        )
    )

    # 3. UserInactiveTargeted
    await event_bus.publish(
        UserInactiveTargeted(
            audit_ctx=ctx,
            actor_id=1,
            actor_name="Admin",
            target_user_id=3,
            action=UserAction.MODIFY,
        )
    )

    # 4. UserUpdateSkipped
    await event_bus.publish(UserUpdateSkipped(audit_ctx=ctx, user_id=4))

    # 5. UserUpdated (in-session)
    await event_bus.publish(
        UserUpdated(audit_ctx=ctx, user_id=5, changes={"name": {"old": "Old", "new": "New"}}),
        session=db_session,
    )

    # 6. UserDeactivated (in-session)
    await event_bus.publish(UserDeactivated(audit_ctx=ctx, user_id=6), session=db_session)

    await db_session.commit()

    # Verify logs exist
    logs, total = await audit_repo.get_multi(limit=50)
    assert total >= 6

    event_types = {entry.event_type for entry in logs}
    assert "USER_NOT_FOUND" in event_types
    assert LogAction.SECURITY_ACCESS_DENIED in event_types
    assert LogAction.USER_DEACTIVATED in event_types
    assert LogAction.USER_UPDATED in event_types


@pytest.mark.asyncio
async def test_auth_domain_events_dispatch(db_session: AsyncSession) -> None:
    """Verifies that all 14 Auth domain events are handled and logged."""
    audit_repo = AuditLogRepository(session=db_session)
    ctx = AuditContext(ip_address="127.0.0.1", user_agent="PyTestClient", request_id="req-auth-1")

    # Failure events (autonomous session)
    await event_bus.publish(
        AuthEmailAlreadyRegistered(audit_ctx=ctx, user_id=10, email="dupe@test.com", name="Dupe")
    )
    await event_bus.publish(
        AuthRegistrationFailed(audit_ctx=ctx, email="fail@test.com", error="DB Constraint")
    )
    await event_bus.publish(AuthEmailNotFound(audit_ctx=ctx, email="ghost@test.com"))
    await event_bus.publish(AuthInvalidPassword(audit_ctx=ctx, user_id=11, email="user@test.com"))
    await event_bus.publish(
        AuthInactiveUserRejected(
            audit_ctx=ctx,
            user_id=12,
            email="deact@test.com",
            action=AuthAction.LOGIN,
        )
    )
    await event_bus.publish(AuthRefreshSessionNotFound(audit_ctx=ctx, user_id=13))
    await event_bus.publish(AuthRefreshSessionExpired(audit_ctx=ctx, user_id=14, session_id=101))
    await event_bus.publish(AuthTokenReplayDetected(audit_ctx=ctx, user_id=15, session_id=102))

    # Success events (in-session)
    await event_bus.publish(
        AuthUserRegistered(audit_ctx=ctx, user_id=16, email="reg@test.com", name="Reg"),
        session=db_session,
    )
    await event_bus.publish(AuthLoggedIn(audit_ctx=ctx, user_id=16), session=db_session)
    await event_bus.publish(AuthTokenPairIssued(audit_ctx=ctx, user_id=16), session=db_session)
    await event_bus.publish(AuthTokenRotated(audit_ctx=ctx, user_id=16), session=db_session)
    await event_bus.publish(AuthLoggedOut(audit_ctx=ctx, user_id=16), session=db_session)
    await event_bus.publish(AuthAllSessionsRevoked(audit_ctx=ctx, user_id=16), session=db_session)

    await db_session.commit()

    logs, total = await audit_repo.get_multi(limit=50)
    assert total >= 14

    auth_actions = {entry.event_type for entry in logs}
    assert LogAction.USER_REGISTERED in auth_actions
    assert LogAction.AUTH_LOGIN_FAILED in auth_actions
    assert LogAction.AUTH_TOKEN_REVOKED in auth_actions
    assert LogAction.AUTH_LOGIN_SUCCESS in auth_actions
    assert LogAction.CUSTOM in auth_actions
    assert LogAction.AUTH_TOKEN_ROTATED in auth_actions
    assert LogAction.AUTH_LOGOUT in auth_actions


@pytest.mark.asyncio
async def test_event_bus_isolation_and_idempotency() -> None:
    """Tests that handler exceptions do not halt the publisher and subscription is idempotent."""
    bus = AsyncEventBus()

    call_count = 0

    class DummyEvent(DomainEvent):
        pass

    async def broken_handler(event: DummyEvent, session: AsyncSession | None) -> None:
        raise RuntimeError("Handler failure simulation")

    async def normal_handler(event: DummyEvent, session: AsyncSession | None) -> None:
        nonlocal call_count
        call_count += 1

    # Idempotent subscription test
    bus.subscribe(DummyEvent, normal_handler)
    bus.subscribe(DummyEvent, normal_handler)
    bus.subscribe(DummyEvent, broken_handler)

    # Publishing must not raise RuntimeError even when broken_handler throws
    await bus.publish(DummyEvent())

    # normal_handler should be called exactly once despite double subscription
    assert call_count == 1
