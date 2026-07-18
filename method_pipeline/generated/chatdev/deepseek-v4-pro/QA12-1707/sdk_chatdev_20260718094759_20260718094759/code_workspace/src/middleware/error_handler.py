"""
Global error handler that maps AppError subclasses to HTTP responses.

ADR-008: Centralised exception-to-HTTP mapping in FastAPI exception handlers.
  Decision: Register handlers for each AppError subclass on the FastAPI app.
  Context: NFR 2.2 (Fault Detection) — consistent error shapes aid monitoring.
  Alternatives: (a) middleware catch-all — less granular;
    (b) per-controller try/except — duplicates code.
  Consequences: All services must raise AppError subclasses for this to work.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
                **exc.extra,
            },
        )

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail, "error_code": "NOT_FOUND"},
        )

    @app.exception_handler(ConflictError)
    async def _conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": exc.detail, "error_code": "CONFLICT"},
        )

    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.detail, "error_code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(ServiceUnavailableError)
    async def _unavailable(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": exc.detail, "error_code": "SERVICE_UNAVAILABLE"},
        )
