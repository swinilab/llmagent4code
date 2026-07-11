"""
Application entry point for the Order Management System.

Starts the FastAPI server with:
  - All API routes under /api/v1/
  - Health check endpoints under /health/
  - Graceful shutdown handling
  - Background worker for task queue processing (unless WORKER_MODE=true)
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from oms.api.controllers import router as api_router
from oms.config import settings
from oms.infrastructure.database import close_db_pool
from oms.infrastructure.cache import close_redis
from oms.infrastructure.health import router as health_router
from oms.worker import start_worker, stop_worker

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("Starting OMS application...")
    worker_task = None
    # Only start embedded worker if not running in dedicated worker mode
    if os.environ.get("WORKER_MODE", "").lower() != "true":
        worker_task = asyncio.create_task(start_worker())
        logger.info("Embedded background worker started")
    else:
        logger.info("Dedicated worker mode — skipping embedded worker")
    logger.info("OMS application started on %s:%d", settings.host, settings.port)
    yield
    # Shutdown
    logger.info("Shutting down OMS application...")
    await stop_worker()
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await close_db_pool()
    await close_redis()
    logger.info("OMS application shut down complete.")


app = FastAPI(
    title="Order Management System",
    description="Production-grade e-commerce OMS backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a structured error response."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Run the application server with a single worker.

    The lifespan handler starts an embedded background worker for task queue
    processing. Using multiple workers (uvicorn --workers N) would create
    competing consumers on the same Redis streams. For production deployments,
    use the Docker CMD which runs a single worker per container, or run
    dedicated worker containers with WORKER_MODE=true.
    """
    uvicorn.run(
        "oms.main:app",
        host=settings.host,
        port=settings.port,
        workers=1,
        log_level="info",
    )


if __name__ == "__main__":
    run()
