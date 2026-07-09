"""
FastAPI application entry point.

Sets up middleware, routers, and lifecycle hooks.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.controllers import (
    customer_controller,
    invoice_controller,
    order_controller,
    payment_controller,
    product_controller,
)
from app.domain.exceptions import DomainError
from app.infrastructure.database import engine
from app.infrastructure.logging import setup_logging
from app.infrastructure.queue import declare_queues, close_queue
from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.metrics import MetricsMiddleware, metrics_collector
from app.middleware.rate_limiter_middleware import RateLimiterMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown."""
    setup_logging()
    logger.info("Starting OMS backend — lifespan startup")

    # Declare RabbitMQ queues
    try:
        await declare_queues()
    except Exception as exc:
        logger.warning("RabbitMQ not available, queues will be declared later: %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down OMS backend")
    await engine.dispose()
    await close_queue()


app = FastAPI(
    title="Order Management System (OMS)",
    version="1.0.0",
    description="Production-grade e-commerce OMS backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware stack (order matters) ──────────────────────────────────
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimiterMiddleware)


# ── Domain-error handler ──────────────────────────────────────────────
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_code": type(exc).__name__},
    )


# ── Health check ──────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "oms"}


# ── Metrics endpoint ──────────────────────────────────────────────────
@app.get("/metrics", tags=["system"])
async def metrics():
    return metrics_collector.snapshot()


# ── Register routers ─────────────────────────────────────────────────
app.include_router(customer_controller.router)
app.include_router(product_controller.router)
app.include_router(order_controller.router)
app.include_router(payment_controller.router)
app.include_router(invoice_controller.router)


# ── Entry point ────────────────────────────────────────────────────────
def run() -> None:
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        loop="uvloop",
        http="httptools",
    )


if __name__ == "__main__":
    run()
