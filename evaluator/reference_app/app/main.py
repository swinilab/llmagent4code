"""FastAPI application: routes, health, metrics, and error mapping.

Middleware order matters and is not arbitrary. Starlette runs the last-added
middleware outermost, so admission control is added after the test hooks and
therefore wraps them -- which puts the injected delay *inside* an admitted slot,
holding it for the full duration. Reversing the two would make the delay run
before admission and the overload stimulus would evaporate.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from . import services
from .admission import AdmissionMiddleware, TestHookMiddleware, clear_fault_state
from .cache import DependencyUnavailable, product_cache
from .config import settings
from .database import (
    DatabaseTimeout,
    database_reachable,
    engine,
    to_controlled,
)
from .models import Base
from .observability import ControlledError, log_event, log_startup, metrics

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Raise the thread limit that synchronous endpoints run on, well above the
    # default of 40. Every sync handler occupies one of these threads, so under
    # a two-hundred-request burst the excess would queue waiting for a thread
    # before reaching admission control -- and a rejection that waits is
    # indistinguishable from the bounded queue this tactic is defined against.
    # Immediate refusal requires the server to be able to pick the request up
    # immediately, which is a property of the runtime, not of the semaphore.
    import anyio

    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 512

    # Schema creation stands in for an Alembic migration here. This application
    # calibrates the tactic scenarios, not the migration requirement, so the
    # schema is created from metadata -- but it is still created automatically
    # at startup with no manual step, which is the property that matters.
    log_event("migration", action="schema_upgrade_started", mechanism="sqlalchemy_metadata")
    Base.metadata.create_all(bind=engine)
    log_event("migration", action="schema_upgrade_complete", mechanism="sqlalchemy_metadata")
    log_startup(settings)
    yield


app = FastAPI(
    title="OrderMan Reference",
    version="1.0.0",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Added inner-first: TestHook runs inside Admission, so the delay holds a slot.
app.add_middleware(TestHookMiddleware)
app.add_middleware(AdmissionMiddleware)


# ── error mapping ─────────────────────────────────────────────────────────


@app.exception_handler(ControlledError)
async def _controlled(_: Request, exc: ControlledError) -> Response:
    return exc.to_response()


@app.exception_handler(DependencyUnavailable)
async def _unavailable(_: Request, exc: DependencyUnavailable) -> Response:
    return to_controlled(exc).to_response()


@app.exception_handler(DatabaseTimeout)
async def _timeout(_: Request, exc: DatabaseTimeout) -> Response:
    return to_controlled(exc).to_response()


@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception) -> Response:
    """Last resort: an unhandled fault still leaves as a classified failure.

    Every scenario asserts zero unhandled 500s, so anything reaching here is a
    defect -- but it should be a legible one rather than a bare stack trace.
    """
    return to_controlled(exc).to_response()


# ── observation paths ─────────────────────────────────────────────────────
# Exempt from admission control and free of database round-trips, so they keep
# answering while the system is saturated or its database is gone.


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> Response:
    """Reports readiness honestly, and answers either way.

    During an outage this must still respond -- reporting not-ready is correct,
    failing to answer is not.
    """
    ready = database_reachable()
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready"},
    )


@app.get("/internal/metrics")
def internal_metrics() -> dict[str, int]:
    if settings.defect_metrics_need_db:
        # Calibration path: observability routed through the failed dependency,
        # so it disappears exactly when the outage makes it necessary.
        database_reachable() or _raise_unavailable()
    return metrics.snapshot()


def _raise_unavailable() -> None:
    raise DependencyUnavailable("metrics require the database")


@app.post("/internal/test/reset", status_code=204)
def internal_reset() -> Response:
    if not settings.enable_test_hooks:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    metrics.reset()
    product_cache.clear()
    clear_fault_state()
    return Response(status_code=204)


# ── entity routes ─────────────────────────────────────────────────────────


@app.post("/api/v1/customers", status_code=201)
def create_customer(body: dict[str, Any]) -> dict[str, Any]:
    return services.create_customer(body)


@app.get("/api/v1/customers/{customer_id}")
def get_customer(customer_id: str) -> dict[str, Any]:
    return services.get_customer(customer_id)


@app.post("/api/v1/products", status_code=201)
def create_product(body: dict[str, Any]) -> dict[str, Any]:
    return services.create_product(body)


@app.get("/api/v1/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    return services.get_product(product_id)


@app.get("/api/v1/products")
def search_products(query: str = "") -> list[dict[str, Any]]:
    return services.search_products(query)


@app.post("/api/v1/orders", status_code=201)
def create_order(body: dict[str, Any]) -> dict[str, Any]:
    return services.create_order(body)


@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str) -> dict[str, Any]:
    return services.get_order(order_id)


@app.post("/api/v1/invoices", status_code=201)
def create_invoice(body: dict[str, Any]) -> dict[str, Any]:
    return services.create_invoice(body)


@app.get("/api/v1/invoices/{invoice_id}")
def get_invoice(invoice_id: str) -> dict[str, Any]:
    return services.get_invoice(invoice_id)


@app.post("/api/v1/payments", status_code=201)
def create_payment(body: dict[str, Any]) -> dict[str, Any]:
    return services.create_payment(body)


@app.get("/api/v1/payments/{payment_id}")
def get_payment(payment_id: str) -> dict[str, Any]:
    return services.get_payment(payment_id)


# ── workflow routes ───────────────────────────────────────────────────────


@app.post("/api/v1/orders/{order_id}/accept")
def accept_order(order_id: str) -> dict[str, Any]:
    return services.transition_order(order_id, "accept")


@app.post("/api/v1/payments/{payment_id}/verify")
def verify_payment(payment_id: str) -> dict[str, Any]:
    return services.verify_payment(payment_id)


@app.post("/api/v1/orders/{order_id}/ship")
def ship_order(order_id: str) -> dict[str, Any]:
    return services.transition_order(order_id, "ship")


@app.post("/api/v1/orders/{order_id}/close")
def close_order(order_id: str) -> dict[str, Any]:
    return services.transition_order(order_id, "close")
