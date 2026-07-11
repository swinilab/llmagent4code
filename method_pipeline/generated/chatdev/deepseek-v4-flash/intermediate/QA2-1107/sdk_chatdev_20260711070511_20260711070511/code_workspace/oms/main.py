"""
Main entry point for the Order Management System backend.

Initializes the database, registers middleware and routers, and starts
the Uvicorn server. Also launches a background thread for outbox processing
(state recovery on restart – NFR 2.3).
"""
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oms.config import settings
from oms.database import SessionLocal, init_db
from oms.middleware.degradation import DegradationMiddleware
from oms.repositories.outbox_repo import OutboxRepository
from oms.routers import (
    customer as customer_router,
    health as health_router,
    invoice as invoice_router,
    order as order_router,
    payment as payment_router,
    product as product_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outbox background worker (NFR 2.3 – State Preservation)
# ---------------------------------------------------------------------------
def _outbox_worker():
    """
    Background thread that polls the outbox table for PENDING messages
    and processes them. On restart, any unprocessed messages left from
    a previous crash are replayed, ensuring no order state is lost.
    """
    logger.info("Outbox worker started – polling every %.1f s",
                 settings.OUTBOX_POLL_INTERVAL)
    while True:
        try:
            db = SessionLocal()
            try:
                repo = OutboxRepository(db)
                pending = repo.get_pending(limit=20)
                for msg in pending:
                    try:
                        _process_outbox_message(msg)
                        repo.mark_processed(msg.id)
                        db.commit()
                        logger.info("Outbox message %s processed: %s",
                                    msg.id, msg.event_type)
                    except Exception as exc:
                        db.rollback()
                        repo.mark_failed(msg.id)
                        db.commit()
                        logger.error("Outbox message %s failed: %s",
                                     msg.id, exc)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Outbox worker error: %s", exc)
        time.sleep(settings.OUTBOX_POLL_INTERVAL)


def _process_outbox_message(msg) -> None:
    """
    Process a single outbox message. In a real system this would publish
    to a message queue, send emails, update search indexes, etc.
    Here we simply log the event.
    """
    payload: Dict = json.loads(msg.payload)
    logger.info(
        "Processing outbox: [%s] %s %s -> %s",
        msg.aggregate_type,
        msg.event_type,
        msg.aggregate_id,
        payload,
    )
    # Simulate side-effect (e.g., send email notification)
    time.sleep(0.05)


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("OMS backend starting up...")
    init_db()

    # Start outbox worker in daemon thread (NFR 2.3)
    worker = threading.Thread(target=_outbox_worker, daemon=True)
    worker.start()
    logger.info("Outbox worker thread launched")

    yield

    logger.info("OMS backend shutting down...")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Order Management System",
    description="Production-grade OMS backend with fault tolerance and state preservation.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Degradation middleware (NFR 2.1)
app.add_middleware(DegradationMiddleware)

# Register routers
app.include_router(health_router.router)
app.include_router(customer_router.router)
app.include_router(product_router.router)
app.include_router(order_router.router)
app.include_router(payment_router.router)
app.include_router(invoice_router.router)


@app.get("/")
def root():
    return {
        "service": "Order Management System",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run():
    """Launch the OMS server."""
    uvicorn.run(
        "oms.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info",
    )


if __name__ == "__main__":
    run()
