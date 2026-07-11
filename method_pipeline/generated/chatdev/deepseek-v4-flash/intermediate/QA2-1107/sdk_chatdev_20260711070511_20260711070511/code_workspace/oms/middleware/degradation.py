"""
Graceful Degradation Middleware (NFR 2.1).

Monitors system resource usage (CPU, memory) and, when thresholds are
exceeded, dynamically disables non-essential features such as:
- Heavy logging / analytics
- Recommendation endpoints (if any)
- Non-critical background tasks

The core checkout flow (order creation, payment, invoice) is never degraded.
"""
import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from oms.config import settings
from oms.utils.system import get_cpu_percent, get_mem_percent

logger = logging.getLogger(__name__)

# Paths that are considered "core" – never degraded
_CORE_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/orders",
    "/api/v1/payments",
    "/api/v1/invoices",
    "/api/v1/customers",
    "/api/v1/products",
    "/api/v1/health",
}

# Paths considered "non-essential" – may be degraded
_NON_ESSENTIAL_PREFIXES = {
    "/api/v1/recommendations",
    "/api/v1/analytics",
    "/api/v1/logs",
    "/api/v1/debug",
}


class DegradationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that checks system load and returns a 503 with a clear
    message for non-essential endpoints when resources are saturated.
    """

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._last_check = 0.0
        self._cached_degraded = False
        self._cache_ttl = 5.0  # re-check every 5 seconds

    async def dispatch(self, request: Request, call_next: Callable):
        degraded = self._check_degradation()

        if degraded and self._is_non_essential(request.url.path):
            logger.warning(
                "Degradation active – rejecting non-essential request %s",
                request.url.path,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "detail": (
                        "System is under heavy load. Non-essential features "
                        "are temporarily disabled. Please try again later."
                    ),
                    "degraded": True,
                },
            )

        response = await call_next(request)
        return response

    def _check_degradation(self) -> bool:
        now = time.monotonic()
        if now - self._last_check < self._cache_ttl:
            return self._cached_degraded

        cpu = get_cpu_percent()
        mem = get_mem_percent()
        self._cached_degraded = (
            cpu > settings.DEGRADATION_CPU_THRESHOLD
            or mem > settings.DEGRADATION_MEM_THRESHOLD
        )
        self._last_check = now
        if self._cached_degraded:
            logger.info(
                "Degradation triggered: cpu=%.1f%% mem=%.1f%%",
                cpu, mem,
            )
        return self._cached_degraded

    @staticmethod
    def _is_non_essential(path: str) -> bool:
        # First check if it's a known non-essential prefix
        for prefix in _NON_ESSENTIAL_PREFIXES:
            if path.startswith(prefix):
                return True
        # Then check if it's a known core path (including docs)
        for core in _CORE_PATHS:
            if path == core or path.startswith(core + "/") or path.startswith(core + "?"):
                return False
        # Unknown paths are treated as core (safe default – Fix 4)
        return False
