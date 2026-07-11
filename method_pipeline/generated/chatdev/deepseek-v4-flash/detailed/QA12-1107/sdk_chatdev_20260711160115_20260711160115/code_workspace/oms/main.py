"""
OMS Application — FastAPI entry point.

Sets up:
  - Database engine
  - Redis cache
  - RabbitMQ connection
  - State recovery on startup
  - Background outbox processor (NFR 2.3)
  - Middleware (rate limiting, logging)
  - Health check endpoints
  - API routes
  - Graceful shutdown
"""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oms.api.controllers import router as api_router
from oms.api.middleware import setup_metrics_endpoint, setup_middleware
from oms.config import settings
from oms.infrastructure.cache import cache
from oms.infrastructure.database import close_db, init_db
from oms.infrastructure.health import router as health_router
from oms.infrastructure.message_queue import mq
from oms.infrastructure.state_recovery import process_outbox, startup_recovery

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("oms")

# How often (in seconds) the background outbox processor polls for pending events
OUTBOX_POLL_INTERVAL_SECONDS = 5


async def _run_outbox_processor():
    """Continuously poll the outbox table and forward events to RabbitMQ.

    This is the background task that makes the Transactional Outbox pattern
    complete (NFR 2.3). Without this, outbox entries would be durably stored
    but never delivered to downstream consumers.

    The task runs as long as the application is alive. On shutdown, it is
    cancelled gracefully.
    """
    logger.info("Background outbox processor started (poll interval=%ds)", OUTBOX_POLL_INTERVAL_SECONDS)
    while True:
        try:
            await process_outbox()
        except asyncio.CancelledError:
            logger.info("Background outbox processor cancelled")
            raise
        except Exception as e:
            logger.error("Outbox processor error: %s", e)
        await asyncio.sleep(OUTBOX_POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("=== OMS Starting Up ===")
    logger.info("Database URL: %s", settings.database_url)
    logger.info("Redis URL: %s", settings.redis_url)
    logger.info("RabbitMQ URL: %s", settings.rabbitmq_url)
    logger.info("Workers: %d, Rate limit: %.0f/s, Burst: %d",
                 settings.workers, settings.rate_limit_refill_rate, settings.rate_limit_burst)

    # Initialize infrastructure
    await init_db()
    logger.info("Database tables initialized")

    await cache.connect()
    logger.info("Redis cache connected")

    await mq.connect()
    logger.info("RabbitMQ connected")

    # State recovery (NFR 2.3) — process any outbox entries that were left
    # unprocessed from a previous crash, then start continuous processing.
    await startup_recovery()

    # Start background outbox processor (NFR 2.3)
    outbox_task = asyncio.create_task(_run_outbox_processor())
    logger.info("Background outbox processor task created")

    yield

    # Shutdown
    logger.info("=== OMS Shutting Down ===")
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass
    logger.info("Background outbox processor stopped")
    await mq.disconnect()
    await cache.disconnect()
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Order Management System (OMS)",
        version="1.0.0",
        description="Production-grade e-commerce Order Management System backend.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware
    setup_middleware(app)

    # Routes
    app.include_router(health_router)
    app.include_router(api_router)

    # Metrics
    setup_metrics_endpoint(app)

    return app


app = create_app()


def run():
    """Run the application with uvicorn."""
    uvicorn.run(
        "oms.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.workers,
        log_level="info",
        loop="uvloop",
        http="httptools",
    )


if __name__ == "__main__":
    run()
