import math
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

_T = TypeVar('_T')


class PaginationParams:
    """FastAPI dependency for extracting pagination query parameters.

    Usage::

        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(),
        ) -> PaginatedResponse[ItemResponse]:
            ...
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


class PaginationMeta(BaseModel):
    """Metadata block describing the current pagination window."""

    page: int
    """Current page number (1-indexed)."""

    page_size: int
    """Number of items per page."""

    total: int
    """Total number of items across all pages."""

    pages: int
    """Total number of pages."""

    @classmethod
    def from_params(
        cls,
        *,
        page: int,
        page_size: int,
        total: int,
    ) -> "PaginationMeta":
        """Factory that computes ``pages`` from the other three values.

        Args:
            page: Current page number.
            page_size: Items per page.
            total: Total item count.

        Returns:
            A fully populated ``PaginationMeta`` instance.
        """
        return cls(
            page=page,
            page_size=page_size,
            total=total,
            pages=max(1, math.ceil(total / page_size)),
        )


class PaginatedResponse(BaseModel, Generic[_T]):
    """Generic paginated list response envelope."""

    success: bool = True
    """Always ``True`` for successful responses."""

    data: list[_T]
    """The page of items."""

    pagination: PaginationMeta
    """Pagination metadata."""


class ErrorDetail(BaseModel):
    """Structured error payload inside ``ErrorResponse``."""

    code: str
    """Machine-readable error code (e.g. ``USER_NOT_FOUND``)."""

    message: str
    """Human-readable error description."""

    details: Any | None = None
    """Optional extra context (validation errors, field-level info)."""


class ErrorResponse(BaseModel):
    """Unified error response envelope returned by all exception handlers."""

    success: bool = False
    """Always ``False`` for error responses."""

    error: ErrorDetail
    """The structured error payload."""

    request_id: str | None = None
    """Correlation ID for log tracing."""


class SuccessResponse(BaseModel, Generic[_T]):
    """Generic single-item success response envelope."""

    success: bool = True
    """Always ``True`` for successful responses."""

    data: _T
    """The response payload."""


class MessageResponse(BaseModel):
    """Simple action-confirmation response (logout, delete, etc.)."""

    success: bool = True
    """Always ``True`` for successful responses."""

    message: str
    """Human-readable confirmation message."""
