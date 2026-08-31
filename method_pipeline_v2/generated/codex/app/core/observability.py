import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter(
    "oms_http_requests_total",
    "HTTP requests handled by the OMS",
    ("method", "path", "status"),
)
REQUEST_DURATION = Histogram(
    "oms_http_request_duration_seconds",
    "OMS HTTP request duration",
    ("method", "path"),
)
OUTBOX_PUBLISHED = Counter("oms_outbox_published_total", "Outbox events published")
OUTBOX_DEFERRED = Counter("oms_outbox_deferred_total", "Outbox publication attempts deferred")
CACHE_FAILURES = Counter("oms_cache_failures_total", "Redis cache operations that failed", ("operation",))
RESYNC_MISMATCHES = Counter("oms_resync_mismatches_total", "Secondary copies repaired", ("entity",))
DEPENDENCY_UP = Gauge("oms_dependency_up", "Dependency health", ("dependency",))


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            path = request.scope.get("route").path if request.scope.get("route") else request.url.path
            REQUEST_COUNT.labels(request.method, path, str(status)).inc()
            REQUEST_DURATION.labels(request.method, path).observe(time.perf_counter() - started)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def configure_observability(app: FastAPI, log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app.add_middleware(RequestContextMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
