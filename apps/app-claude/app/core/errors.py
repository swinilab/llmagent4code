"""Controlled error contract shared by every failure path.

The four codes are mutually exclusive by cause, and the distinction is load
bearing: ASR-A1 requires DEPENDENCY_TIMEOUT for an exceeded per-attempt time
limit, while ASR-A3 requires DEPENDENCY_UNAVAILABLE when the database cannot be
reached at all. Classification happens at the database boundary, where the real
cause is observable, never at the HTTP layer.
"""

from __future__ import annotations

from typing import Any

DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
OVERLOAD_REJECTED = "OVERLOAD_REJECTED"
TRANSACTION_FAILED = "TRANSACTION_FAILED"


def error_body(code: str, message: str, **extra: Any) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    error.update(extra)
    return {"error": error}


class ControlledError(Exception):
    """A failure that must surface as the prescribed JSON error envelope."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message

    def body(self) -> dict[str, Any]:
        return error_body(self.code, self.message)


class DependencyTimeoutError(ControlledError):
    """Bounded retry policy exhausted with every attempt exceeding its limit."""

    def __init__(self, message: str = "Database operation exceeded the configured time limit.") -> None:
        super().__init__(504, DEPENDENCY_TIMEOUT, message)


class DependencyUnavailableError(ControlledError):
    """The database could not be reached, or a write needs durable state."""

    def __init__(self, message: str = "The database dependency is currently unavailable.") -> None:
        super().__init__(503, DEPENDENCY_UNAVAILABLE, message)


class OverloadRejectedError(ControlledError):
    """Admission control refused the request; the in-flight limit was reached."""

    def __init__(self, message: str = "The in-flight request limit was reached; retry shortly.") -> None:
        super().__init__(429, OVERLOAD_REJECTED, message)


class TransactionFailedError(ControlledError):
    """A transaction was rolled back due to an internal fault."""

    def __init__(self, message: str = "The transaction was rolled back; no partial state was committed.") -> None:
        super().__init__(500, TRANSACTION_FAILED, message)


class DomainError(Exception):
    """Business-rule failure mapped to 400/404/409 by the API error handlers."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class NotFoundError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(404, "NOT_FOUND", message)


class ConflictError(DomainError):
    """Workflow or referential-state conflict."""

    def __init__(self, message: str) -> None:
        super().__init__(409, "STATE_CONFLICT", message)


class ValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "VALIDATION_ERROR", message)
