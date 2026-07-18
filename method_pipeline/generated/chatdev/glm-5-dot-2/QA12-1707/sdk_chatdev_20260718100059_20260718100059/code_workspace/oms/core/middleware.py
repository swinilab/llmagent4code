"""
ASGI middleware for cross-cutting concerns.

- GracefulDegradationMiddleware: NFR 2.1 — monitors system resources and
  degrades non-essential endpoints when under contention.
- RequestTimingMiddleware: NFR 1.1 — logs response times for core journeys.
- HealthCheckMiddleware: NFR 2.2 — provides /health and /health/ready endpoints.
"""
import logging
import time
from typing import Any

import psutil
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from oms.config import settings

logger = logging.getLogger(__name__)

# Endpoints considered "non-essential" — can be degraded under load.
# NOTE: /api/v1/customers is intentionally excluded from non-essential because
# customer creation is part of the core checkout workflow (you cannot place an
# order without a customer).  Only truly ancillary features (e.g. product
# search) are degraded so the ordering journey always remains available.
NON_ESSENTIAL_PREFIXES = (
    "/api/v1/products/search",
)

# Endpoints considered "core" — must remain available
CORE_PREFIXES = (
    "/api/v1/orders",
    "/api/v1/payments",
    "/api/v1/invoices",
    "/api/v1/customers",
)


class GracefulDegradationMiddleware(BaseHTTPMiddleware):
    """
    Monitors CPU and memory usage. When either exceeds the configured
    threshold, non-essential endpoints receive 503 responses while core
    checkout endpoints continue to be served.

    This satisfies NFR 2.1 (Graceful Degradation).

    All psutil calls use interval=None (non-blocking) so the ASGI event loop
    is never stalled.  This preserves NFR 1.1 (Response Time) and NFR 1.2
    (Concurrency & Resource Utilization) — the blocking interval=0.5 variant
    would sleep 500 ms on the event loop and stall every concurrent request.
    """

    def __init__(self, app, cpu_threshold: float | None = None,
                 memory_threshold: float | None = None) -> None:
        super().__init__(app)
        self.cpu_threshold = cpu_threshold or settings.degradation_cpu_threshold
        self.memory_threshold = memory_threshold or settings.degradation_memory_threshold
        self._degraded = False
        self._last_check = 0.0
        # Prime the first non-blocking read so the next cpu_percent(interval=None)
        # returns a meaningful value instead of 0.0.  Also primes memory stats.
        # These calls return immediately and establish an internal baseline.
        psutil.cpu_percent(interval=None)
        psutil.virtual_memory()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check resource usage at most every N seconds
        now = time.monotonic()
        if now - self._last_check > settings.degradation_check_interval:
            self._last_check = now
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            if cpu >= self.cpu_threshold or mem >= self.memory_threshold:
                if not self._degraded:
                    logger.warning(
                        "Graceful degradation ACTIVE (cpu=%.1f%%, mem=%.1f%%) — "
                        "non-essential endpoints disabled",
                        cpu, mem,
                    )
                self._degraded = True
            else:
                if self._degraded:
                    logger.info(
                        "Graceful degradation LIFTED (cpu=%.1f%%, mem=%.1f%%) — "
                        "all endpoints restored",
                        cpu, mem,
                    )
                self._degraded = False

        # If degraded and request targets a non-essential endpoint, reject
        if self._degraded:
            path = request.url.path
            if any(path.startswith(p) for p in NON_ESSENTIAL_PREFIXES):
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Service temporarily degraded. Non-essential features are disabled.",
                        "degraded": True,
                    },
                )

        return await call_next(request)

    @property
    def is_degraded(self) -> bool:
        return self._degraded


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """
    Logs request duration for observability of response times (NFR 1.1).
    Adds an X-Response-Time header to every response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
        if duration_ms > 500:
            logger.warning(
                "Slow request: %s %s took %.2fms",
                request.method, request.url.path, duration_ms,
            )
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Intercepts /health and /health/ready before routing.

    /health       — liveness probe (always 200 if process is alive)
    /health/ready — readiness probe (checks DB + circuit breakers + queue)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path == "/health":
            return JSONResponse(
                status_code=200,
                content={"status": "alive", "service": settings.app_name},
            )
        if path == "/health/ready":
            checks: dict[str, Any] = {}

            # Database check
            try:
                from oms.database import engine
                if engine is not None:
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                    checks["database"] = "ok"
                else:
                    checks["database"] = "not_initialised"
            except Exception as exc:
                checks["database"] = f"error: {exc}"

            # Circuit breaker check
            from oms.core.resilience import circuit_breaker_registry
            breaker_statuses = circuit_breaker_registry.all_status()
            open_breakers = [b for b in breaker_statuses if b["state"] == "open"]
            checks["circuit_breakers"] = {
                "open_count": len(open_breakers),
                "details": breaker_statuses,
            }

            # Queue check
            from oms.core.queue_manager import queue_manager
            checks["queue"] = queue_manager.status()

            all_ok = (
                checks.get("database") == "ok"
                and len(open_breakers) == 0
            )
            return JSONResponse(
                status_code=200 if all_ok else 503,
                content={"status": "ready" if all_ok else "degraded", "checks": checks},
            )

        return await call_next(request)