"""OMS Backend - Main application entry point.

FastAPI application with:
  - Versioned REST API (v1)
  - Prometheus metrics endpoint
  - Correlation ID middleware
  - Structured logging
  - Rate limiting on checkout path
  - Circuit breakers for downstream dependencies
  - Cache-aside (Redis) for product browse
  - RabbitMQ for deferrable work
  - Background consumer for deferred work processing
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.metrics_controller import record_metrics_middleware, router as metrics_router
from app.api.v1.order_controller import router as order_router
from app.api.v1.product_controller import router as product_router
from app.config import settings
from app.infrastructure.cache import close_cache, init_cache
from app.infrastructure.database import close_db, init_db
from app.infrastructure.messaging import close_messaging, init_messaging, start_consumer
from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.logging_middleware import setup_logging

logger = logging.getLogger(__name__)


async def _work_handler(work_type: str, payload: dict) -> None:
    """Handle deferred work items from the RabbitMQ queue.

    This is the consumer-side processor for deferrable spike-absorbed work.
    In production, this would dispatch to specific handlers based on work_type.
    """
    logger.info("Processing deferred work: type=%s, payload=%s", work_type, payload)
    # In production, dispatch to specific handlers:
    # if work_type == "generate_invoice": ...
    # elif work_type == "send_notification": ...
    await asyncio.sleep(0.01)  # Simulated processing time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()
    logger.info(
        "Starting OMS Backend",
        extra={
            "workers": settings.uvicorn_workers,
            "db_pool_size": settings.db_pool_size,
            "rate_limit_capacity": settings.rate_limit_capacity,
            "rate_limit_refill": settings.rate_limit_refill_per_second,
        },
    )

    await init_db()
    logger.info("Database initialized")

    await init_cache()
    logger.info("Cache (Redis) initialized")

    await init_messaging()
    logger.info("Messaging (RabbitMQ) initialized")

    # Start the background consumer for deferred work processing
    # This is a critical fix: previously the consumer was never started,
    # so deferrable work was published to RabbitMQ but never consumed.
    consumer_task = asyncio.create_task(start_consumer(_work_handler))
    logger.info("RabbitMQ consumer started for deferred work processing")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await close_messaging()
    await close_cache()
    await close_db()
    logger.info("OMS Backend shut down")


# ── FastAPI Application ──────────────────────────────────────────────────

app = FastAPI(
    title="Order Management System API",
    description="Production-grade e-commerce OMS backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CorrelationIDMiddleware)

# Metrics middleware (wraps all routes)
app.middleware("http")(record_metrics_middleware)

# Routers
app.include_router(order_router)
app.include_router(product_router)
app.include_router(metrics_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name}


def run() -> None:
    """Run the application server."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.uvicorn_workers,
        limit_concurrency=settings.uvicorn_limit_concurrency,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
