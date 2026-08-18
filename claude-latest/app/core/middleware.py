"""Cross-cutting HTTP middleware.

``RateLimitMiddleware``       - NFR 1.1, admission control at the edge.
``ExceptionDetectionMiddleware`` - NFR 2.1, converts unhandled faults and
                                overruns into structured, counted responses.
"""
import asyncio
import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import DomainError
from app.infra.degradation import feature_registry

logger = logging.getLogger(__name__)

# Ops endpoints stay reachable while the service is shedding load, otherwise an
# operator loses observability exactly when they need it.
_LIMIT_EXEMPT_PREFIXES = ("/health", "/ops", "/docs", "/openapi.json", "/redoc")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """NFR 1.1 - Limit Event Response.

    Rejects with 429 above the configured sustained rate instead of queueing,
    so overload is bounded rather than absorbed into unbounded latency.
    """

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in _LIMIT_EXEMPT_PREFIXES):
            return await call_next(request)

        limiter = request.app.state.rate_limiter
        identity = request.headers.get("X-Client-Id") or (
            request.client.host if request.client else "anonymous"
        )

        if not await limiter.allow(identity):
            request.app.state.metrics["throttled"] += 1
            retry_after = max(1, int(1 / max(limiter.refill_rate, 0.001)))
            logger.warning("throttled %s on %s", identity, request.url.path)
            return JSONResponse(
                status_code=429,
                content={
                    "code": "rate_limited",
                    "message": "request rate exceeds the configured maximum",
                    "detail": {"capacity": limiter.capacity, "refillPerSecond": limiter.refill_rate},
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


class ExceptionDetectionMiddleware(BaseHTTPMiddleware):
    """NFR 2.1 - Exception Detection (system exceptions + timeout).

    Every request gets a correlation id, a wall-clock budget, and a single place
    where an unexpected fault becomes a structured 500 rather than a bare stack
    trace. Slow requests are surfaced as 504 rather than hanging a client.
    """

    def __init__(self, app, request_timeout_seconds: float = 10.0) -> None:
        super().__init__(app)
        self.request_timeout = request_timeout_seconds

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        started = time.perf_counter()
        metrics = request.app.state.metrics

        try:
            response = await asyncio.wait_for(call_next(request), timeout=self.request_timeout)
        except asyncio.TimeoutError:
            metrics["exceptions_detected"] += 1
            metrics["timeouts"] += 1
            logger.error("timeout on %s cid=%s", request.url.path, correlation_id)
            return JSONResponse(
                status_code=504,
                content={
                    "code": "timeout",
                    "message": "request exceeded its processing budget",
                    "correlationId": correlation_id,
                },
            )
        except DomainError:
            raise  # handled by the registered domain exception handler
        except Exception:
            metrics["exceptions_detected"] += 1
            logger.exception("unhandled system exception cid=%s", correlation_id)
            # NFR 2.2: a fault in a non-critical path sheds that feature rather
            # than taking the service down.
            if request.url.path.endswith("/history"):
                feature_registry.shed("order_history_expansion")
            return JSONResponse(
                status_code=500,
                content={
                    "code": "internal_error",
                    "message": "an unexpected internal error occurred",
                    "correlationId": correlation_id,
                },
            )

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Correlation-Id"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response
