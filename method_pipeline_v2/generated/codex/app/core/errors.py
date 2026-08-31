from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class BadRequestError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(400, "bad_request", message, details)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(404, "not_found", f"{resource} '{identifier}' was not found")


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "state_conflict", message)


class DependencyUnavailableError(AppError):
    def __init__(self, dependency: str) -> None:
        super().__init__(503, "dependency_unavailable", f"{dependency} is unavailable")


def _payload(request: Request, code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "requestId": getattr(request.state, "request_id", None),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "location": ".".join(str(part) for part in item["loc"] if part != "body"),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=_payload(request, "validation_error", "Request validation failed", details),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("database_integrity_error", exc_info=exc)
        return JSONResponse(
            status_code=409,
            content=_payload(request, "integrity_conflict", "The request conflicts with stored data"),
        )

    @app.exception_handler(DBAPIError)
    async def handle_database_error(request: Request, exc: DBAPIError) -> JSONResponse:
        logger.error("database_system_exception", exc_info=exc)
        return JSONResponse(
            status_code=503,
            content=_payload(request, "database_unavailable", "The system of record is unavailable"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_system_exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_payload(request, "internal_error", "An unexpected system error occurred"),
        )

