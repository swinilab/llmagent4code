"""
Prometheus metrics exposition.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# ── HTTP metrics ─────────────────────────────────────────────────────────────
http_request_duration = Histogram(
    "oms_http_request_duration_seconds",
    "HTTP request latency (seconds)",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    labelnames=["method", "endpoint", "status"],
)

http_requests_total = Counter(
    "oms_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

# ── Business metrics ─────────────────────────────────────────────────────────
orders_created = Counter("oms_orders_created_total", "Total orders created")

# Counter for order status transitions (each transition is a discrete event).
# Use a Counter rather than a Gauge because we only ever increment; a Gauge
# would require decrementing the old status on every transition, which adds
# complexity and risk of drift. A separate background job can compute the
# point-in-time count per status from the database if needed.
orders_transitions = Counter(
    "oms_orders_transitions_total",
    "Total order status transitions",
    labelnames=["to_status"],
)

# ── Queue metrics ────────────────────────────────────────────────────────────
queue_depth = Gauge("oms_queue_depth", "Current RabbitMQ queue depth")

# ── Rate limiter ─────────────────────────────────────────────────────────────
rate_limiter_tokens = Gauge("oms_rate_limiter_tokens", "Available tokens in bucket")

# ── Circuit breaker ──────────────────────────────────────────────────────────
circuit_breaker_state = Gauge(
    "oms_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    labelnames=["name"],
)


def get_metrics() -> str:
    """Return Prometheus-formatted metrics."""
    return generate_latest().decode("utf-8")
