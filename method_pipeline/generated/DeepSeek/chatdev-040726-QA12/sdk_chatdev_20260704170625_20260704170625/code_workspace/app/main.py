"""FastAPI application entry point.

Binds routers, middleware, queue lifecycle, and serves the OpenAPI spec.
On startup, auto-creates database tables for development convenience.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.init_db import create_tables
from app.middleware.queue_manager import queue_manager
from app.middleware.rate_limiter import RateLimitMiddleware
from app.routers.v1.customer_router import router as customer_router
from app.routers.v1.invoice_router import router as invoice_router
from app.routers.v1.order_router import router as order_router
from app.routers.v1.payment_router import router as payment_router
from app.routers.v1.product_router import router as product_router
from app.services.workflow_service import WorkflowError

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("oms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background queue worker on startup, stop on shutdown."""
    logger.info("Starting OMS backend...")
    await create_tables()
    queue_manager.start()
    yield
    logger.info("Shutting down OMS backend...")
    await queue_manager.stop()


app = FastAPI(
    title="Order Management System (OMS)",
    description="Production-grade backend for e-commerce order lifecycle management.\n"
    "Roles: Customer, Order Staff, Accountant.\n"
    "Full workflow: place \u2192 accept \u2192 invoice \u2192 pay \u2192 verify \u2192 ship \u2192 close.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Global exception handlers ─────────────────────────────────────────────────
# WorkflowError must propagate through get_db() so that session.rollback()
# runs before the response is sent.  The global handler below converts the
# exception into a 409 Conflict response after the DB transaction has been
# rolled back, ensuring ACID guarantees (NFR 1.2).


@app.exception_handler(WorkflowError)
async def workflow_error_handler(request: Request, exc: WorkflowError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

# ── Routers (v1 versioned paths — NFR 2.2) ──────────────────────────────────
app.include_router(customer_router)
app.include_router(order_router)
app.include_router(invoice_router)
app.include_router(payment_router)
app.include_router(product_router)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "queue_size": queue_manager.size}