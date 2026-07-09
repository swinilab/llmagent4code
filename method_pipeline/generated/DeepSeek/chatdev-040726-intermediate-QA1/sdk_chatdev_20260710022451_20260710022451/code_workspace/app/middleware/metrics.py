"""
Simple in-memory metrics collector exposed via a /metrics endpoint.

Captures:
  - Request count (total, by path, by status)
  - Latency histogram (buckets in ms)
  - Queue depth (approximate from rate limiter)
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.rate_limiter import get_rate_limiter


class MetricsCollector:
    """Thread-safe (asyncio) metrics store."""

    def __init__(self) -> None:
        self._lock = None  # asyncio.Lock created lazily
        self.request_count: dict[str, int] = defaultdict(int)
        self.status_count: dict[int, int] = defaultdict(int)
        self.latencies: dict[str, list[float]] = defaultdict(list)

    async def record(self, path: str, status: int, latency_ms: float) -> None:
        import asyncio
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self.request_count[path] += 1
            self.status_count[status] += 1
            bucket = self.latencies[path]
            bucket.append(latency_ms)
            # Keep only last 10 000 samples per path
            if len(bucket) > 10_000:
                bucket[:] = bucket[-5_000:]

    def snapshot(self) -> dict:
        """Return a dict suitable for /metrics output."""
        import statistics
        data = {
            "request_count": dict(self.request_count),
            "status_count": dict(self.status_count),
            "latency": {},
        }
        for path, vals in self.latencies.items():
            if not vals:
                continue
            sorted_vals = sorted(vals)
            n = len(sorted_vals)
            data["latency"][path] = {
                "p50_ms": sorted_vals[int(n * 0.50)],
                "p95_ms": sorted_vals[int(n * 0.95)],
                "p99_ms": sorted_vals[int(n * 0.99)],
                "count": n,
            }
        # Rate limiter state
        limiter = get_rate_limiter()
        data["rate_limiter"] = {
            "available_tokens": limiter.available_tokens,
            "max_tokens": 200,
        }
        return data


metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        await metrics_collector.record(
            path=request.url.path,
            status=response.status_code,
            latency_ms=elapsed_ms,
        )
        return response
