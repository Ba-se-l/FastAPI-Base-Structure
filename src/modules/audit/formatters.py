import json
from collections.abc import Sequence

from .enum import ExportFormat
from .schemas import LogResponse


class BaseLogFormatter:
    """Base interface for serializing audit log entries."""

    def format_single(self, log: LogResponse) -> str:
        """Serializes a single log record.

        Args:
            log: The log entry to serialize.

        Returns:
            Formatted string representation.
        """
        raise NotImplementedError

    def format_batch(self, logs: Sequence[LogResponse]) -> str:
        """Serializes multiple log records into a consolidated document.

        Args:
            logs: Sequence of log entries.

        Returns:
            Consolidated formatted document string.
        """
        raise NotImplementedError


class JsonLogFormatter(BaseLogFormatter):
    """Formats audit logs as standard JSON or JSON Lines (NDJSON)."""

    def format_single(self, log: LogResponse) -> str:
        """Serializes single record as single-line JSON string."""
        return json.dumps(log.model_dump(mode='json'), ensure_ascii=False, indent=2)

    def format_batch(self, logs: Sequence[LogResponse]) -> str:
        """Serializes a collection of records as a formatted JSON array."""
        payload = [log.model_dump(mode='json') for log in logs]
        return json.dumps(payload, indent=2, ensure_ascii=False)


class TextLogFormatter(BaseLogFormatter):
    """Formats audit logs as standardized human-readable plain text lines."""

    def format_single(self, log: LogResponse) -> str:
        """Formats a single record into a log line:

        [YYYY-MM-DD HH:MM:SS UTC] [SEVERITY] [USER: id] [REQ: id] EVENT_TYPE — Message
        """
        ts = log.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        user_part = f"[USER: {log.user_id}]" if log.user_id else "[USER: -]"
        req_part = f"[REQ: {log.request_id}]" if log.request_id else "[REQ: -]"
        return f"[{ts}] [{log.severity:<8}] {user_part} {req_part} {log.event_type} — {log.message}"

    def format_batch(self, logs: Sequence[LogResponse]) -> str:
        """Joins multiple formatted log lines separated by newlines."""
        return '\n'.join(self.format_single(log) for log in logs)


class MarkdownLogFormatter(BaseLogFormatter):
    """Formats audit logs into a clean GitHub-Flavored Markdown table."""

    def format_single(self, log: LogResponse) -> str:
        """Formats single record as a markdown table row."""
        ts = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        user = log.user_id or '-'
        req = log.request_id or '-'
        msg = log.message.replace('|', '\\|')
        return f"| {log.id} | {ts} | `{log.severity}` | `{log.event_type}` | {user} | {req} | {msg} |"

    def format_batch(self, logs: Sequence[LogResponse]) -> str:
        """Formats a list of records with a markdown table header."""
        header = (
            '# 📜 Audit Trail Export\n\n'
            '| ID | Timestamp (UTC) | Severity | Event Type | User ID | Request ID | Message |\n'
            '|---|---|---|---|---|---|---|'
        )
        if not logs:
            return f"{header}\n| - | - | - | *No matching audit events* | - | - | - |\n"

        rows = [self.format_single(log) for log in logs]
        return f"{header}\n" + '\n'.join(rows) + '\n'


_FORMATTERS: dict[ExportFormat, BaseLogFormatter] = {
    ExportFormat.JSON: JsonLogFormatter(),
    ExportFormat.TXT: TextLogFormatter(),
    ExportFormat.MARKDOWN: MarkdownLogFormatter(),
}


def get_formatter(fmt: ExportFormat) -> BaseLogFormatter:
    """Factory retrieving the configured formatter instance for a format.

    Args:
        fmt: Desired export format.

    Returns:
        The matched formatter instance.
    """
    return _FORMATTERS[fmt]
