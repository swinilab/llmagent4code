"""
Domain exceptions with structured error codes for consistent API responses.

ADR-003: Use a single exception hierarchy with HTTP-mapped codes.
  Decision: Custom exception classes inheriting from a base AppError.
  Context: NFR 2.2 (Fault Detection) — structured errors enable precise logging.
  Alternatives: (a) plain HTTPException — no domain semantics; (b) problem-details RFC — heavier.
  Consequences: Every service layer raise must use these; controllers catch and map.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error with HTTP status code."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "", extra: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}


class NotFoundError(AppError):
    """Resource not found (404)."""

    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppError):
    """Resource conflict / duplicate (409)."""

    status_code = 409
    error_code = "CONFLICT"


class ValidationError(AppError):
    """Business rule violation (422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class PaymentError(AppError):
    """Payment processing failure (402)."""

    status_code = 402
    error_code = "PAYMENT_ERROR"


class ServiceUnavailableError(AppError):
    """Downstream service unavailable (503) — used by circuit breaker."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"


class RateLimitError(AppError):
    """Too many requests (429)."""

    status_code = 429
    error_code = "RATE_LIMITED"
