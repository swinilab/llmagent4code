"""
Main FastAPI application entry point for the Order Management System.
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import engine, Base
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
    workflow_router,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("oms")
logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
))
logger.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified")
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request timing middleware (NFR 1.1 observability) ---
class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Logs request duration for latency monitoring."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        if elapsed > 0.5:
            logger.warning(
                "SLOW REQUEST | %s %s | %.3fs",
                request.method, request.url.path, elapsed,
            )
        return response

app.add_middleware(RequestTimingMiddleware)

# --- Rate Limiting (NFR 1.3) ---
app.add_middleware(RateLimitMiddleware, rate_limit=settings.rate_limit_per_minute)

# --- Routers ---
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(invoice_router)
app.include_router(workflow_router)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return a 500."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Health & OpenAPI endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/openapi.yaml", tags=["OpenAPI"])
def get_openapi_yaml():
    """Return the OpenAPI spec as YAML."""
    import yaml
    return JSONResponse(
        content=yaml.safe_load(app.openapi()),
    )
