"""
Rate-limiting middleware using a sliding-window counter per IP address
with periodic cleanup of stale entries to prevent memory leaks.

Uses an integer-based approach (tracking request timestamps in a deque)
to avoid floating-point drift that can accumulate in token-bucket refill
calculations over long-running deployments.
"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter per IP address using a deque of timestamps.

    Satisfies NFR 1.3 (Queue Management) by rejecting requests
    that exceed the configured threshold instead of letting them
    queue up and crash the system.

    Stale entries are cleaned up every CLEANUP_INTERVAL seconds
    to prevent unbounded memory growth.
    """

    CLEANUP_INTERVAL = 300.0  # 5 minutes
    STALE_AGE = 600.0  # 10 minutes without activity → eligible for cleanup

    def __init__(self, app, rate_limit: int = settings.rate_limit_per_minute):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = 60.0  # 1 minute in seconds
        # Each IP maps to a deque of request timestamps (in seconds)
        self.requests: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=rate_limit + 1)
        )
        self._last_cleanup = time.time()

    def _cleanup_stale_entries(self) -> None:
        """Remove entries that have not been accessed for STALE_AGE seconds."""
        now = time.time()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        stale_ips = [
            ip for ip, dq in self.requests.items()
            if dq and now - dq[-1] > self.STALE_AGE
        ]
        for ip in stale_ips:
            del self.requests[ip]
        self._last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        # Opportunistic cleanup of stale entries
        self._cleanup_stale_entries()

        now = time.time()
        dq = self.requests[client_ip]

        # Remove timestamps outside the sliding window
        while dq and dq[0] <= now - self.window:
            dq.popleft()

        if len(dq) >= self.rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        dq.append(now)
        return await call_next(request)
