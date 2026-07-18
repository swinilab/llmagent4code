"""
OMS Backend — main application entry point.

Wires together all layers: database, middleware, routers, and
lifecycle hooks (startup recovery, queue management, graceful shutdown).

Run with:
    uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from oms.config import settings
from oms.core.middleware import (
    GracefulDegradationMiddleware,
    HealthCheckMiddleware,
    RequestTimingMiddleware,
)
from oms.core.queue_manager import queue_manager
from oms.core.recovery import RecoveryService
import oms.database as db
from oms.routers.v1 import v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle:

    Startup:
      1. Initialise database (WAL mode, create tables).
      2. Run state recovery scan (NFR 2.3).
      3. Start background queue workers (NFR 1.3).

    Shutdown:
      1. Stop queue workers gracefully.
      2. Dispose database engine.
    """
    logger.info("OMS Backend starting up...")

    # 1. Database
    await db.init_db()
    logger.info("Database initialised (WAL mode enabled)")

    # 2. State recovery (NFR 2.3)
    # Access the factory as a module attribute so we observe the value
    # reassigned by init_db() (which declares it `global`). Importing the
    # name directly (`from oms.database import async_session_factory`)
    # would capture the stale `None` bound at import time, silently
    # skipping the recovery scan — see NFR 2.3.
    if db.async_session_factory is not None:
        async with db.async_session_factory() as session:
            recovery = RecoveryService(session)
            summary = await recovery.recover()
            logger.info("Recovery summary: %s", summary)
    await queue_manager.start()
    logger.info("Queue workers started")

    logger.info("OMS Backend ready — serving on %s:%d", settings.host, settings.port)
    yield

    # Shutdown
    logger.info("OMS Backend shutting down...")
    await queue_manager.stop()
    await queue_manager.stop()
    await db.dispose_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Production-grade Order Management System backend. "
            "Serves the complete workflow: customer ordering → payment "
            "processing → invoicing → shipping → closure."
        ),
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Middleware (order matters: outermost first)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(GracefulDegradationMiddleware)
    app.add_middleware(HealthCheckMiddleware)

    # Routes
    app.include_router(v1_router)

    return app


app = create_app()