"""
Rate limiter middleware using an in-memory sliding window.
Satisfies NFR 1.1 (Response Time) by preventing abuse and NFR 1.3 (Queue Management)
by shedding excess load before it reaches the application.

Includes periodic cleanup of stale entries to prevent unbounded memory growth.
"""
import time
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.config import settings

logger = logging.getLogger(__name__)

# How often (in dispatch calls) to trigger a full cleanup of stale IP entries
_CLEANUP_INTERVAL = 100


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter per client IP.
    Returns 429 Too Many Requests when the limit is exceeded.

    Periodically purges entries for IPs that have no recent activity to
    prevent unbounded memory growth under high traffic.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._dispatch_count = 0

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - settings.rate_limit_window_seconds

        # Periodic full cleanup to prevent unbounded memory growth
        self._dispatch_count += 1
        if self._dispatch_count % _CLEANUP_INTERVAL == 0:
            self._purge_stale_entries(now, window_start)

        # Purge old entries for this IP
        self._windows[client_ip] = [t for t in self._windows[client_ip] if t > window_start]

        if len(self._windows[client_ip]) >= settings.rate_limit_requests:
            logger.warning("Rate limit exceeded for IP %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": settings.rate_limit_window_seconds,
                },
            )

        self._windows[client_ip].append(now)
        return await call_next(request)

    def _purge_stale_entries(self, now: float, window_start: float) -> None:
        """Remove IP entries whose last activity is older than the window."""
        stale_ips = [
            ip
            for ip, timestamps in self._windows.items()
            if not timestamps or max(timestamps) < window_start
        ]
        for ip in stale_ips:
            del self._windows[ip]
        if stale_ips:
            logger.debug("Rate limiter cleanup: removed %d stale IP entries", len(stale_ips))
