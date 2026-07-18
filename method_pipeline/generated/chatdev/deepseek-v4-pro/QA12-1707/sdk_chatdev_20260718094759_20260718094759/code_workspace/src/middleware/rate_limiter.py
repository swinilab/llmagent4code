"""
Token-bucket rate limiter (NFR 1.3 Queue Management).

ADR-006: In-memory token-bucket rate limiter as ASGI middleware.
  Decision: Token-bucket algorithm with configurable rate and burst.
  Context: NFR 1.3 (Queue Management) — prevents sudden spikes from crashing the system.
  Alternatives: (a) Redis-based — adds infrastructure dependency;
    (b) fixed-window — less smooth under burst.
  Consequences: In-memory means per-process limits; acceptable for single-node deployment.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.config import settings


class RateLimiter:
    """Token-bucket rate limiter per client IP."""

    def __init__(
        self,
        rate: float | None = None,
        burst: int | None = None,
    ) -> None:
        self.rate = rate or settings.rate_limit_requests_per_second
        self.burst = burst or settings.rate_limit_burst_size
        self._buckets: dict[str, tuple[float, float]] = defaultdict(
            lambda: (time.monotonic(), self.burst)
        )

    def allow(self, key: str) -> bool:
        """Return True if the request is allowed for the given key."""
        now = time.monotonic()
        last_check, tokens = self._buckets[key]
        elapsed = now - last_check
        tokens = min(self.burst, tokens + elapsed * self.rate)
        if tokens >= 1:
            self._buckets[key] = (now, tokens - 1)
            return True
        self._buckets[key] = (now, tokens)
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that applies rate limiting."""

    def __init__(self, app, limiter: RateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self.limiter.allow(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests", "error_code": "RATE_LIMITED"},
            )
        return await call_next(request)
