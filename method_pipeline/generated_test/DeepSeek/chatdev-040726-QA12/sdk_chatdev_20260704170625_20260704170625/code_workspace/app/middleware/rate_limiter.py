"""Simple in-memory rate limiter for NFR 1.1 (response time under load).

Uses a sliding-window counter per client IP. Returns 429 when limit exceeded.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter — configurable window & max requests."""

    def __init__(
        self,
        app: object,
        max_requests: int = 200,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Only apply to API paths
        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._buckets[client_ip]

        # Prune expired timestamps
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )

        bucket.append(now)
        return await call_next(request)