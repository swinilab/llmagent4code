"""
ASGI middleware that applies token-bucket rate limiting only to the
checkout hot-path endpoints (POST /api/v1/orders, POST /api/v1/payments).
Read operations and back-office PATCH requests pass through freely.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.infrastructure.rate_limiter import get_rate_limiter

# (method, path_prefix) pairs that are guarded by the rate limiter.
# Only checkout write operations are rate-limited — read operations
# (GET) and back-office transitions (PATCH) are exempt.
RATE_LIMITED_ENDPOINTS: set[tuple[str, str]] = {
    ("POST", "/api/v1/orders"),
    ("POST", "/api/v1/payments"),
}

# Paths that are exempt (health, metrics, docs) — checked FIRST
EXEMPT_PREFIXES = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Reject requests to rate-limited endpoints with 429 when the token
    bucket is empty. Only POST requests to checkout paths are throttled."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        method = request.method

        # Exempt non-critical paths — checked BEFORE rate-limited paths
        if any(path.startswith(p) for p in EXEMPT_PREFIXES):
            return await call_next(request)

        # Only rate-limit specific (method, path_prefix) pairs
        if (method, path) not in RATE_LIMITED_ENDPOINTS:
            return await call_next(request)

        limiter = get_rate_limiter()
        allowed = await limiter.try_consume()
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please retry after the rate limit window.",
                    "retry_after_seconds": 1,
                },
                headers={"Retry-After": "1", "X-RateLimit-Limit": "200"},
            )

        return await call_next(request)
