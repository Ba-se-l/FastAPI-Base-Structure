import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.settings import settings
from .enum import ExportFormat, LogAction, LogSeverity
from .formatters import get_formatter
from .model import AuditLog
from .repo import AuditLogRepository
from .schemas import LogEvent, LogExportParams, LogQueryFilter, LogResponse

logger = logging.getLogger(__name__)


def _append_to_file_sync(log_dir: str, log_resp: LogResponse) -> None:
    """Synchronous file writer invoked via worker thread to avoid event loop blocking."""
    try:
        dir_path = Path(log_dir)
        dir_path.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # 1. Append JSON Line
        json_file = dir_path / f"{date_str}.json"
        json_line = get_formatter(ExportFormat.JSON).format_single(log_resp) + '\n'
        with open(json_file, 'a', encoding='utf-8') as f:
            f.write(json_line)

        # 2. Append Human-readable TXT
        txt_file = dir_path / f"{date_str}.txt"
        txt_line = get_formatter(ExportFormat.TXT).format_single(log_resp) + '\n'
        with open(txt_file, 'a', encoding='utf-8') as f:
            f.write(txt_line)

        # 3. Append Markdown Row
        md_file = dir_path / f"{date_str}.md"
        md_row = get_formatter(ExportFormat.MARKDOWN).format_single(log_resp) + '\n'
        is_new = not md_file.exists() or md_file.stat().st_size == 0
        with open(md_file, 'a', encoding='utf-8') as f:
            if is_new:
                header = (
                    '# 📜 Daily Audit Log\n\n'
                    '| ID | Timestamp (UTC) | Severity | Event Type | User ID | Request ID | Message |\n'
                    '|---|---|---|---|---|---|---|\n'
                )
                f.write(header)
            f.write(md_row)
    except Exception as exc:
        logger.warning('Failed to append audit log to disk: %s', exc)


async def log_event(event: LogEvent, session: AsyncSession) -> LogResponse:
    """Central maestro orchestrating audit logging across database and file storage.

    Args:
        event: Validated LogEvent payload.
        session: Active async database session.

    Returns:
        Persisted LogResponse representation.
    """
    repo = AuditLogRepository(session=session)

    # 1. Build and persist to database
    audit_instance = AuditLog(
        event_type=event.event_type,
        severity=event.severity.value,
        message=event.message,
        user_id=event.user_id,
        request_id=event.request_id,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        extra_data=event.extra_data,
    )

    if settings.log_to_db:
        audit_instance = await repo.create(audit_instance)
        await session.flush()

    response = LogResponse.model_validate(audit_instance)

    # 2. Asynchronous non-blocking file output
    if settings.log_to_file:
        asyncio.create_task(
            asyncio.to_thread(_append_to_file_sync, settings.log_dir, response)
        )

    return response


async def save_success_event(
    message: str,
    *,
    session: AsyncSession,
    event_type: str | LogAction = LogAction.CUSTOM,
    user_id: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> LogResponse:
    """Specialist helper for recording successful state transitions with INFO severity."""
    action_str = event_type.value if isinstance(event_type, LogAction) else event_type
    event = LogEvent(
        event_type=action_str,
        severity=LogSeverity.INFO,
        message=message,
        user_id=user_id,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data,
    )
    return await log_event(event, session=session)


async def save_failed_event(
    message: str,
    *,
    session: AsyncSession,
    event_type: str | LogAction = LogAction.SYSTEM_ERROR,
    severity: LogSeverity = LogSeverity.ERROR,
    user_id: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> LogResponse:
    """Specialist helper for recording failures or security warnings."""
    action_str = event_type.value if isinstance(event_type, LogAction) else event_type
    event = LogEvent(
        event_type=action_str,
        severity=severity,
        message=message,
        user_id=user_id,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data,
    )
    return await log_event(event, session=session)


async def query_audit_logs(
    filter_params: LogQueryFilter,
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[LogResponse], int]:
    """Retrieves paginated audit log entries matching filter parameters."""
    repo = AuditLogRepository(session=session)
    items, total = await repo.query_logs(filter_params, offset=offset, limit=limit)
    return [LogResponse.model_validate(item) for item in items], total


async def get_user_audit_logs(
    user_id: str,
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[LogResponse], int]:
    """Retrieves all audit entries linked specifically to a single user identifier."""
    repo = AuditLogRepository(session=session)
    items, total = await repo.get_by_user(user_id, offset=offset, limit=limit)
    return [LogResponse.model_validate(item) for item in items], total


async def export_audit_logs(
    params: LogExportParams,
    session: AsyncSession,
    *,
    max_records: int = 1000,
) -> tuple[str, str, str]:
    """Exports matching audit logs into a formatted document for download.

    Args:
        params: Export criteria and target format.
        session: Active database session.
        max_records: Upper threshold for exported records.

    Returns:
        Tuple of (content_string, media_type, download_filename).
    """
    filter_params = LogQueryFilter(
        user_id=params.user_id,
        event_type=params.event_type,
        severity=params.severity,
        from_date=params.from_date,
        to_date=params.to_date,
    )

    repo = AuditLogRepository(session=session)
    items = await repo.get_all_matching(filter_params, max_records=max_records)
    responses = [LogResponse.model_validate(item) for item in items]

    formatter = get_formatter(params.format)
    content = formatter.format_batch(responses)

    # Resolve filename & content type
    target_tag = f"user_{params.user_id}" if params.user_id else 'audit'
    now_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"{target_tag}_{now_str}.{params.format.value}"

    media_types = {
        ExportFormat.JSON: 'application/json',
        ExportFormat.TXT: 'text/plain; charset=utf-8',
        ExportFormat.MARKDOWN: 'text/markdown; charset=utf-8',
    }

    return content, media_types[params.format], filename
