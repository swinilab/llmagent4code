"""
Custom exceptions and FastAPI exception handlers for the OMS.
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.state_machine import IllegalTransitionError

logger = logging.getLogger(__name__)


class NotFoundError(ValueError):
    """Raised when a requested entity is not found."""


class ConflictError(ValueError):
    """Raised on optimistic lock conflict or duplicate idempotency key."""


async def illegal_transition_handler(
    request: Request, exc: IllegalTransitionError
) -> JSONResponse:
    """Handle illegal state transition errors."""
    logger.warning(
        "Illegal transition: %s -> %s", exc.from_status.value, exc.event.value
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "error_code": "ILLEGAL_TRANSITION",
            "from_status": exc.from_status.value,
            "event": exc.event.value,
        },
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle not-found errors."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "error_code": "NOT_FOUND"},
    )


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Handle conflict errors (optimistic locking, duplicates)."""
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "error_code": "CONFLICT"},
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle generic value errors (validation, business rules)."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_code": "BAD_REQUEST"},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )
