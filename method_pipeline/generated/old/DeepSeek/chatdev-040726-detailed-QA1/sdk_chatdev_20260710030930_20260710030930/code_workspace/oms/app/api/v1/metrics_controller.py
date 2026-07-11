"""Prometheus metrics endpoint for runtime instrumentation.

Exposes metrics in the standard Prometheus exposition format (text/plain).
Key metrics for NFR verification:
  - http_request_duration_seconds (histogram): p50/p95/p99 latency
  - http_requests_total (counter): throughput
  - http_errors_total (counter): error rate
  - rate_limiter_tokens_available (gauge): queue depth / admission control
  - circuit_breaker_state (gauge): 0=CLOSED, 1=OPEN, 2=HALF_OPEN
  - db_connection_pool_size (gauge): active DB connections
  - queue_depth (gauge): RabbitMQ queue depth
"""

import time
from typing import Any

from fastapi import APIRouter, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from app.infrastructure.circuit_breaker import CircuitState, payment_gateway_cb, shipping_api_cb
from app.infrastructure.rate_limiter import checkout_rate_limiter
router = APIRouter(tags=["metrics"])

# ── Prometheus Metrics ──────────────────────────────────────────────────
from app.config import settings
from app.infrastructure.circuit_breaker import CircuitState, payment_gateway_cb, shipping_api_cb
http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0],
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors (4xx/5xx)",
    ["method", "endpoint", "status_code"],
)

rate_limiter_tokens = Gauge(
    "rate_limiter_tokens_available",
    "Available tokens in the rate limiter bucket",
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state: 0=CLOSED, 1=OPEN, 2=HALF_OPEN",
    ["breaker_name"],
)

db_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
)

queue_depth = Gauge(
    "queue_depth",
    "Message queue depth",
    ["queue_name"],
)


def _cb_state_value(state: CircuitState) -> int:
    mapping = {
        CircuitState.CLOSED: 0,
        CircuitState.OPEN: 1,
        CircuitState.HALF_OPEN: 2,
    }
    return mapping.get(state, 0)


def update_metrics() -> None:
    """Update gauge metrics with current values."""
    rate_limiter_tokens.set(checkout_rate_limiter.available_tokens)
    circuit_breaker_state.labels(breaker_name="payment_gateway").set(
        _cb_state_value(payment_gateway_cb.state)
    )
    circuit_breaker_state.labels(breaker_name="shipping_api").set(
        _cb_state_value(shipping_api_cb.state)
    )
    # DB pool size is static from config
    db_pool_size.set(settings.db_pool_size)


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    update_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

async def record_metrics_middleware(request: Request, call_next: Any) -> Response:
    """Middleware to record HTTP request metrics."""
    method = request.method
    endpoint = request.url.path
    start_time = time.perf_counter()
    status_code = 500  # Default in case of early exception before call_next

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.perf_counter() - start_time
        http_request_duration.observe(duration)
        http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
        if status_code >= 400:
            http_errors_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
