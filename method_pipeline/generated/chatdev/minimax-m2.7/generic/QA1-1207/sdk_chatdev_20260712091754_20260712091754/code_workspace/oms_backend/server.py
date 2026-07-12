"""
OMS Backend — FastAPI application entry point.

Gunicorn workers use uvloop for high-concurrency I/O (NFR 1.2).
Graceful shutdown drains in-flight requests before worker replacement (NFR 1.3).
"""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oms_backend.api.v1 import api_router
from oms_backend.core.config import get_settings
from oms_backend.core.rate_limiter import check_rate_limit
from oms_backend.db.connection import check_db_health, close_db, get_database

log = logging.getLogger("oms_backend")


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup DB pool warm-up, shutdown drain."""
    # Startup
    log.info("OMS Backend starting up...")
    settings = get_settings()
    log.info(f"Database: {settings.database.host}:{settings.database.port}/{settings.database.name}")
    log.info(f"Redis: {settings.redis.host}:{settings.redis.port}/{settings.redis.db}")

    # Warm up DB connection pool
    db = get_database()
    try:
        await db.connect()
        log.info("Database connection pool established")
    except Exception as exc:
        log.error(f"Failed to connect to database: {exc}")
        sys.exit(1)

    yield

    # Shutdown: drain in-flight requests
    log.info("OMS Backend shutting down gracefully...")
    await close_db()
    log.info("Database connections closed. Goodbye.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="OMS Backend API",
        description="Order Management System — complete order lifecycle from cart to closure.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware (NFR 1.3)
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health/readiness endpoints
        if request.url.path in ("/health", "/ready", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Extract customer_id from query param or JWT if present
        customer_id = None
        customer_id_param = request.query_params.get("customer_id")
        if customer_id_param:
            try:
                import uuid
                customer_id = uuid.UUID(customer_id_param)
            except ValueError:
                pass

        result = await check_rate_limit(customer_id=customer_id)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after": result.retry_after_seconds},
                headers={"Retry-After": str(result.retry_after_seconds or 60)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response

    # Health endpoints
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["Health"])
    async def ready():
        db_ok = await check_db_health()
        if not db_ok:
            return JSONResponse(status_code=503, content={"status": "db_unavailable"})
        return {"status": "ready"}

    # OpenAPI spec at /openapi.json (used by ADR-002 / NFR 2.2)
    app.include_router(api_router)

    return app


# Alias
app = create_app()


def run() -> None:
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "oms_backend.server:app",
        host=settings.app.host,
        port=settings.app.port,
        log_level=settings.app.log_level.lower(),
        reload=settings.app.debug,
        loop="uvloop",
    )


if __name__ == "__main__":
    run()
