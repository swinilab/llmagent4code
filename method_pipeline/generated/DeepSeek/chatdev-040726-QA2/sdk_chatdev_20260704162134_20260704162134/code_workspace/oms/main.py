"""
Application entry point.
Creates and configures the FastAPI application with all routers and middleware.
"""

import logging

import uvicorn
from fastapi import FastAPI

from oms.config import settings
from oms.middleware.error_handler import register_error_handlers
from oms.api.v1 import customers, products, orders, invoices, payments

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title=settings.openapi_title,
        version=settings.openapi_version,
        description=settings.openapi_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Register global error handlers
    register_error_handlers(app)

    # Mount versioned routers (NFR 2.2 — Interface Stability)
    app.include_router(customers.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(invoices.router)
    app.include_router(payments.router)

    @app.get("/health", tags=["system"])
    def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    """Run the application server."""
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.info("Starting OMS server on %s:%s", settings.host, settings.port)
    uvicorn.run(
        "oms.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    run()
