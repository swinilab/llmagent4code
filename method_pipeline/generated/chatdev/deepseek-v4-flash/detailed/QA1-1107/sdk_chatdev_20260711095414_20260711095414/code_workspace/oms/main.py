"""
Main FastAPI application entry point.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oms.controllers.health_controller import router as health_router
from oms.controllers.order_controller import router as order_router
from oms.controllers.product_controller import router as product_router
from oms.controllers.customer_controller import router as customer_router
from oms.infrastructure.cache import close_redis
from oms.infrastructure.config import settings
from oms.infrastructure.database import engine
from oms.infrastructure.entities import Base
from oms.infrastructure.queue import close_queue, start_queue_depth_sampler
from oms.middleware.correlation_id import CorrelationIDMiddleware
from oms.middleware.logging_config import setup_logging
from oms.middleware.metrics_middleware import MetricsMiddleware

logger = logging.getLogger(__name__)

# Global reference to the queue depth sampler task so it can be cancelled on shutdown
_queue_depth_sampler_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup/shutdown."""
    setup_logging()
    logger.info("Starting OMS backend — FastAPI + PostgreSQL + Redis + RabbitMQ")

    # Create tables (dev mode; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data (idempotent — skips if already seeded)
    try:
        from oms.seed import seed
        await seed()
    except Exception as e:
        logger.warning("Seed skipped or failed: %s", e)

    # Start the queue depth sampler background task (NFR 1.3 monitoring)
    global _queue_depth_sampler_task
    _queue_depth_sampler_task = await start_queue_depth_sampler(interval_seconds=5.0)
    logger.info("Queue depth sampler started (interval=5s)")

    yield  # Application runs here

    # Shutdown
    if _queue_depth_sampler_task is not None:
        _queue_depth_sampler_task.cancel()
        try:
            await _queue_depth_sampler_task
        except asyncio.CancelledError:
            pass
    await close_redis()
    await close_queue()
    await engine.dispose()
    logger.info("OMS backend shut down")


app = FastAPI(
    title="Order Management System",
    version="1.0.0",
    description="Production-grade e-commerce OMS backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (order matters: outermost first)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(MetricsMiddleware)
app.add_middleware(CorrelationIDMiddleware)

# Routers
app.include_router(health_router)
app.include_router(order_router)
app.include_router(product_router)
app.include_router(customer_router)


def run() -> None:
    """Entry point for running the server."""
    uvicorn.run(
        "oms.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level="info",
    )


if __name__ == "__main__":
    run()
