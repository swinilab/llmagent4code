"""
Prometheus HTTP metrics middleware — records latency and request count.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from oms.infrastructure.metrics import http_request_duration, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record HTTP request duration and count for every request."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = time.perf_counter() - start

        # Normalize path for label cardinality
        path = request.url.path
        http_request_duration.labels(
            method=request.method,
            endpoint=path,
            status=str(response.status_code),
        ).observe(elapsed)

        http_requests_total.labels(
            method=request.method,
            endpoint=path,
            status=str(response.status_code),
        ).inc()

        return response
