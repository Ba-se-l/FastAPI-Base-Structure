import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.audit import (
    ExportFormat,
    LogAction,
    LogSeverity,
    export_audit_logs,
    get_user_audit_logs,
    save_failed_event,
    save_success_event,
)
from src.modules.audit.schemas import LogExportParams
from src.modules.user import User, UserRepository
from src.security import create_access_token, hash_password
from src.share import Roles


@pytest.mark.asyncio
async def test_audit_service_operations(db_session: AsyncSession):
    """Tests programmatic service logging, querying, and formatting."""
    # 1. Log success event for user 101
    log1 = await save_success_event(
        message='User logged in via biometric verification',
        event_type=LogAction.AUTH_LOGIN_SUCCESS,
        user_id='101',
        request_id='req-alpha-1',
        ip_address='192.168.1.50',
        extra_data={'method': 'fingerprint'},
        session=db_session,
    )
    assert log1.id is not None
    assert log1.severity == 'INFO'
    assert log1.user_id == '101'

    # 2. Log failed event for user 101
    log2 = await save_failed_event(
        message='Failed payment attempt for invoice #99',
        event_type=LogAction.SYSTEM_ERROR,
        severity=LogSeverity.WARNING,
        user_id='101',
        session=db_session,
    )
    assert log2.severity == 'WARNING'

    # 3. Log event for another user 202
    await save_success_event(
        message='User 202 profile updated',
        event_type=LogAction.USER_UPDATED,
        user_id='202',
        session=db_session,
    )
    await db_session.commit()

    # 4. Query logs specific to user 101
    user_101_logs, total_101 = await get_user_audit_logs('101', session=db_session)
    assert total_101 == 2
    assert len(user_101_logs) == 2
    assert all(entry.user_id == '101' for entry in user_101_logs)

    # 5. Test Export in all 3 formats for user 101
    # a. JSON export
    json_content, json_media, json_file = await export_audit_logs(
        LogExportParams(format=ExportFormat.JSON, user_id='101'),
        session=db_session,
    )
    assert json_media == 'application/json'
    assert json_file.endswith('.json')
    parsed_json = json.loads(json_content)
    assert len(parsed_json) == 2

    # b. TXT export
    txt_content, txt_media, txt_file = await export_audit_logs(
        LogExportParams(format=ExportFormat.TXT, user_id='101'),
        session=db_session,
    )
    assert 'text/plain' in txt_media
    assert txt_file.endswith('.txt')
    assert '[USER: 101]' in txt_content
    assert 'AUTH_LOGIN_SUCCESS' in txt_content

    # c. Markdown export
    md_content, md_media, md_file = await export_audit_logs(
        LogExportParams(format=ExportFormat.MARKDOWN, user_id='101'),
        session=db_session,
    )
    assert 'text/markdown' in md_media
    assert md_file.endswith('.md')
    assert '| ID | Timestamp (UTC) | Severity |' in md_content
    assert '`AUTH_LOGIN_SUCCESS`' in md_content


@pytest.mark.asyncio
async def test_audit_api_endpoints_and_rbac(client: AsyncClient, db_session: AsyncSession):
    """Tests administrative HTTP endpoints for audit log querying, filtering, and export."""
    user_repo = UserRepository(session=db_session)

    # 1. Seed Admin & Normal User
    admin = User(
        name='Security Officer',
        email='sec-admin@enterprise.io',
        hashed_password=hash_password('SecAdmin123!'),
        role=Roles.ADMIN,
        is_active=True,
    )
    await user_repo.create(admin)

    normal_user = User(
        name='Regular Employee',
        email='employee@enterprise.io',
        hashed_password=hash_password('Employee123!'),
        role=Roles.USER,
        is_active=True,
    )
    await user_repo.create(normal_user)
    await db_session.commit()

    admin_token = create_access_token(user_id=admin.id)
    user_token = create_access_token(user_id=normal_user.id)

    # 2. Seed audit log entries
    await save_success_event(
        message='Root login from corporate network',
        event_type=LogAction.AUTH_LOGIN_SUCCESS,
        user_id=str(admin.id),
        session=db_session,
    )
    await save_failed_event(
        message='Unauthorized sensitive file read attempt',
        event_type=LogAction.SECURITY_ACCESS_DENIED,
        severity=LogSeverity.CRITICAL,
        user_id=str(normal_user.id),
        session=db_session,
    )
    await db_session.commit()

    # 3. Normal user denied access -> 403 Forbidden
    denied_resp = await client.get(
        '/api/v1/audit/logs',
        headers={'Authorization': f'Bearer {user_token}'},
    )
    assert denied_resp.status_code == 403
    assert denied_resp.json()['error']['code'] == 'ACCESS_DENIED'

    # 4. Admin accesses logs list -> 200 OK
    admin_resp = await client.get(
        '/api/v1/audit/logs',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert admin_resp.status_code == 200
    list_data = admin_resp.json()
    assert list_data['success'] is True
    assert list_data['pagination']['total'] >= 2

    # 5. Admin accesses user-specific audit trail
    user_logs_resp = await client.get(
        f'/api/v1/audit/users/{normal_user.id}/logs',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert user_logs_resp.status_code == 200
    user_trail = user_logs_resp.json()
    assert user_trail['pagination']['total'] == 1
    assert user_trail['data'][0]['user_id'] == str(normal_user.id)
    assert user_trail['data'][0]['severity'] == 'CRITICAL'

    # 6. Admin downloads export file in Markdown
    export_resp = await client.get(
        f'/api/v1/audit/users/{normal_user.id}/export?format=md',
        headers={'Authorization': f'Bearer {admin_token}'},
    )
    assert export_resp.status_code == 200
    assert 'text/markdown' in export_resp.headers['content-type']
    assert 'attachment; filename="user_' in export_resp.headers['content-disposition']
    assert '| ID | Timestamp (UTC) | Severity |' in export_resp.text
    assert 'SECURITY_ACCESS_DENIED' in export_resp.text
