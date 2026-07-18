"""
Middleware for graceful degradation and recovery.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.recovery import RecoveryService
import structlog

logger = structlog.get_logger(__name__)


class GracefulDegradationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle graceful degradation."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error("Request failed, triggering recovery", error=str(e))
            RecoveryService.recover_pending_orders()
            RecoveryService.recover_failed_tasks()  # Trigger task recovery
            raise