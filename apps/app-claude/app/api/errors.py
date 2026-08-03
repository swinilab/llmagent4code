"""Exception handlers producing the prescribed JSON error envelope.

All public JSON validation failures map to 400. Malformed UUIDs arrive as
Pydantic/path-conversion failures and therefore also produce 400, while a
well-formed but unknown UUID reaches the service layer and produces 404.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.errors import ControlledError, DomainError, error_body
from app.core.logging import log_event


def _first_message(exc: RequestValidationError | PydanticValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Request validation failed"
    first = errors[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = first.get("msg", "invalid value")
    return f"{location}: {message}" if location else message


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ControlledError)
    async def _controlled(_: Request, exc: ControlledError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.body())

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=error_body(exc.code, exc.message)
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_body("VALIDATION_ERROR", _first_message(exc)),
        )

    @app.exception_handler(PydanticValidationError)
    async def _pydantic_validation(_: Request, exc: PydanticValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_body("VALIDATION_ERROR", _first_message(exc)),
        )

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400, content=error_body("VALIDATION_ERROR", str(exc))
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # A genuine unexpected fault. It is logged with full type information so
        # that an unhandled 500 during a scenario is diagnosable from the logs.
        log_event(
            "unhandled_error",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "An unexpected internal error occurred."),
        )
