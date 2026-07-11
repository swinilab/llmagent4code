"""
Order Management System — Application Entry Point.

FastAPI application with:
- Versioned REST API (v1)
- Circuit breaker for non-essential services (NFR 2.1)
- Retry with exponential backoff for DB operations (NFR 2.2)
- State recovery on startup (NFR 2.3)
- Health check endpoint
- Transactional outbox for reliable event publishing
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.outbox import OutboxWorker
from app.api.customers import router as customers_router
from app.api.health import router as health_router
from app.api.invoices import router as invoices_router
from app.api.orders import router as orders_router
from app.api.payments import router as payments_router
from app.api.products import router as products_router
from app.api.recommendations import router as recommendations_router
from app.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    conflict_handler,
    general_exception_handler,
    illegal_transition_handler,
    not_found_handler,
    value_error_handler,
)
from app.core.logging import configure_logging
from app.domain.state_machine import IllegalTransitionError
from app.infrastructure.database import async_session_factory
from app.infrastructure.lifecycle import shutdown_routine, startup_routine

logger = logging.getLogger(__name__)

# ── Outbox worker (background task) ────────────────────────────────────────
_outbox_worker: OutboxWorker | None = None


async def _outbox_polling_loop() -> None:
    """Background task that polls the outbox table for unprocessed messages."""
    global _outbox_worker
    _outbox_worker = OutboxWorker(async_session_factory)
    logger.info("Outbox worker started (poll interval=%ss)", settings.OUTBOX_POLL_INTERVAL)
    while True:
        try:
            await _outbox_worker.process_messages()
        except Exception as exc:
            logger.error("Outbox worker error: %s", exc)
        await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown routines."""
    # ── Startup ───────────────────────────────────────────────────────────
    configure_logging(debug=False)
    await startup_routine()

    # Start the outbox background worker
    outbox_task = asyncio.create_task(_outbox_polling_loop())

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    outbox_task.cancel()
    try:
        await outbox_task
    except asyncio.CancelledError:
        pass
    await shutdown_routine()


# ── FastAPI Application ────────────────────────────────────────────────────
app = FastAPI(
    title="Order Management System",
    description="Production-grade e-commerce OMS backend with graceful degradation, "
    "automated fault recovery, and crash-safe state preservation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# ── Middleware ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────────────────
app.add_exception_handler(IllegalTransitionError, illegal_transition_handler)
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(ConflictError, conflict_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(invoices_router)
app.include_router(recommendations_router)


# ── Entry point ────────────────────────────────────────────────────────────
def run() -> None:
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        log_level="info",
        timeout_keep_alive=settings.REQUEST_TIMEOUT,
    )


if __name__ == "__main__":
    run()
