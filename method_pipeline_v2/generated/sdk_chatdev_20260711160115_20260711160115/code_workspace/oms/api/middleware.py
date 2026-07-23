"""
FastAPI middleware for rate limiting, request logging, and metrics.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from oms.infrastructure.circuit_breaker import get_all_circuit_breaker_metrics
from oms.infrastructure.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiting middleware (NFR 1.3)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)

        allowed = await rate_limiter.try_consume()
        if not allowed:
            logger.warning("Rate limit exceeded for %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "1"},
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request duration and status."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def setup_middleware(app: FastAPI):
    """Register all middleware in order."""
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)


def setup_metrics_endpoint(app: FastAPI):
    """Add a /metrics endpoint for Prometheus-style instrumentation."""

    @app.get("/metrics")
    async def metrics():
        """Expose internal metrics for load-test instrumentation."""
        import json
        available = await rate_limiter.get_available_tokens()
        data = {
            "rate_limiter": {
                "available_tokens": available,
                "refill_rate": rate_limiter._refill_rate,
                "burst": rate_limiter._burst,
            },
            "circuit_breakers": get_all_circuit_breaker_metrics(),
        }
        return data
