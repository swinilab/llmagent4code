"""
OMS Application entry point.

Creates the FastAPI app, registers middleware, routers, error handlers,
and manages the database lifecycle.

Start with:
    python -m src.main
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.controllers import (
    customer_router,
    invoice_router,
    order_router,
    payment_router,
    product_router,
    workflow_router,
)
from src.database import dispose_engine, init_db
from src.middleware.error_handler import register_error_handlers
from src.middleware.rate_limiter import RateLimitMiddleware

logger = logging.getLogger("oms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB; Shutdown: dispose engine."""
    logger.info("Initialising database…")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down…")
    await dispose_engine()
    logger.info("Engine disposed.")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Order Management System",
        description="Production-grade e-commerce OMS backend",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # ── CORS ───────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate Limiting (NFR 1.3) ────────────────────────────
    app.add_middleware(RateLimitMiddleware)

    # ── Error Handlers (NFR 2.2) ───────────────────────────
    register_error_handlers(app)

    # ── Routers ────────────────────────────────────────────
    app.include_router(customer_router)
    app.include_router(product_router)
    app.include_router(order_router)
    app.include_router(payment_router)
    app.include_router(invoice_router)
    app.include_router(workflow_router)

    # ── Health check ───────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Liveness probe."""
        return {"status": "healthy"}

    return app


app = create_app()


def main() -> None:
    """Run the application via uvicorn."""
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
