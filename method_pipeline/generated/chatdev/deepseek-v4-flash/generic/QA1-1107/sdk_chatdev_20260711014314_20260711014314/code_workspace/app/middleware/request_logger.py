"""
Request logging middleware.
Logs method, path, status, and duration for every request.
Helps with observability and NFR verification.
"""
import time
import logging

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("oms.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs each HTTP request with timing information."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
