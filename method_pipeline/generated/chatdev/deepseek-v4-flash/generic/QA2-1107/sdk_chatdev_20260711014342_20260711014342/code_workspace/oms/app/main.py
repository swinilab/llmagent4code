"""
Main application entry point - FastAPI app with lifecycle, health, and recovery.
"""
from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.infrastructure import (
    check_database_health,
    get_circuit_breaker_states,
    recover_pending_orders,
)
from app.models import engine, init_db
from app.routes import register_routes
from app.schemas import HealthResponse

logger = logging.getLogger("oms")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup → yield → shutdown."""
    logger.info("OMS Backend starting up ...")
    init_db()
    logger.info("Database tables created / verified.")

    # ---- State Preservation: recover pending orders on restart ----
    SessionLocal = sessionmaker(bind=engine)
    recovery_session: Session = SessionLocal()
    try:
        recovered = recover_pending_orders(recovery_session)
        if recovered:
            logger.info("Recovered %d pending order(s) from event log.", len(recovered))
            for r in recovered:
                logger.info("  Recovered order %s (status=%s)", r["order_id"], r["status"])
        else:
            logger.info("No pending orders to recover.")
    except Exception as exc:
        logger.warning("Order recovery encountered an issue: %s", exc)
    finally:
        recovery_session.close()

    yield  # application runs here

    logger.info("OMS Backend shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_routes(app)


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
def health_check():
    """Health check - reports database status and circuit breaker states."""
    db_health = check_database_health()
    cb_states = get_circuit_breaker_states()
    return HealthResponse(
        status="healthy" if db_health == "healthy" else "degraded",
        database=db_health,
        circuit_breakers=cb_states,
        version=settings.app_version,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers,
        log_level="info",
    )


if __name__ == "__main__":
    run()
