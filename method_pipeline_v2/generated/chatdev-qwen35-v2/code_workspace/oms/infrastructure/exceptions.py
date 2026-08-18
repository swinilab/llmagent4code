"""
Exception handling infrastructure for NFR 2.1 Exception Detection and NFR 2.2 Graceful Degradation
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

class OMSException(HTTPException):
    """Base exception for OMS application"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code

class ValidationException(OMSException):
    """Validation error exception (400)"""
    def __init__(self, detail: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, error_code=error_code)

class NotFoundException(OMSException):
    """Resource not found exception (404)"""
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, error_code=error_code)

class ConflictException(OMSException):
    """Conflict exception for state machine violations (409)"""
    def __init__(self, detail: str, error_code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, error_code=error_code)

class TransactionException(OMSException):
    """Transaction failure exception (500)"""
    def __init__(self, detail: str = "Transaction failed", error_code: str = "TRANSACTION_ERROR"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail, error_code=error_code)

class RateLimitExceededException(OMSException):
    """Rate limit exceeded exception (429)"""
    def __init__(self, detail: str = "Rate limit exceeded", error_code: str = "RATE_LIMIT_EXCEEDED"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail, error_code=error_code)

class ServiceUnavailableException(OMSException):
    """Service unavailable for graceful degradation (503)"""
    def __init__(self, detail: str = "Service temporarily unavailable", error_code: str = "SERVICE_UNAVAILABLE"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail, error_code=error_code)

async def oms_exception_handler(request: Request, exc: OMSException) -> JSONResponse:
    """Handle OMS exceptions"""
    logger.error(f"OMS Exception: {exc.detail}", exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code or "ERROR",
            "message": exc.detail,
            "path": str(request.url.path)
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors"""
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "path": str(request.url.path)
        }
    )

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors with graceful degradation"""
    logger.error(f"Database Error: {str(exc)}", exc_info=exc)
    # NFR 2.2 Graceful Degradation - return 503 for DB failures
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "DATABASE_ERROR",
            "message": "Database temporarily unavailable",
            "path": str(request.url.path)
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with graceful degradation"""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=exc)
    # NFR 2.2 Graceful Degradation - maintain critical functions
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "path": str(request.url.path)
        }
    )

__all__ = [
    'OMSException', 'ValidationException', 'NotFoundException',
    'ConflictException', 'TransactionException', 'RateLimitExceededException',
    'ServiceUnavailableException',
    'oms_exception_handler', 'validation_exception_handler',
    'sqlalchemy_exception_handler', 'generic_exception_handler'
]
