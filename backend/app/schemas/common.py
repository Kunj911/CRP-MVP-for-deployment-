"""
app/schemas/common.py

Shared Pydantic schemas used across the whole application.

- Standard API response envelopes (success / error / paginated)
- Pagination query params
- Timestamp mixin
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Response envelopes ────────────────────────────────────────────────────────

class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard success envelope.

    Usage:
        return SuccessResponse(data=order, message="Order created")
    """
    success: bool = True
    data: T
    message: str = "OK"


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated list envelope.

    Usage:
        return PaginatedResponse(data=orders, meta=meta)
    """
    success: bool = True
    data: list[T]
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope — produced by the global exception handler."""
    success: bool = False
    error: ErrorDetail


# ── Pagination query params ───────────────────────────────────────────────────

class PaginationParams(BaseModel):
    """Reusable dependency for paginated list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def make_meta(self, total: int) -> PaginationMeta:
        import math
        return PaginationMeta(
            total=total,
            page=self.page,
            per_page=self.per_page,
            pages=math.ceil(total / self.per_page) if total > 0 else 0,
        )


# ── Shared mixins ─────────────────────────────────────────────────────────────

class TimestampMixin(BaseModel):
    """Include in any response schema that returns DB-backed timestamps."""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IDMixin(BaseModel):
    id: int

    model_config = {"from_attributes": True}


# ── Convenience helper ────────────────────────────────────────────────────────

def success(data: Any, message: str = "OK") -> dict:
    """
    Quick helper for returning a plain dict success response.
    Prefer SuccessResponse[T] for typed routes.
    """
    return {"success": True, "data": data, "message": message}
