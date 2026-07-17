"""
Main FastAPI application setup.
Configures middleware, routes, and lifecycle events.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from oms.config.database import db
from oms.controllers import (
    customer_router,
    product_router,
    order_router,
    invoice_router,
    payment_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    Implements state preservation and fault detection.
    """
    logger.info("Starting OMS application...")
    
    try:
        await db.initialize()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    logger.info("Shutting down OMS application...")
    await db.shutdown()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Order Management System (OMS)",
    description="Production-grade e-commerce order management backend",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests for monitoring and debugging."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )
    return response

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        return await call_next(request)
    except Exception as e:
        import traceback
        logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {str(e)}"}
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for fault detection.
    Returns system status and database connectivity.
    """
    db_healthy = await db.health_check()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": time.time(),
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check for load balancers."""
    db_healthy = await db.health_check()
    if not db_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "database_disconnected"}
        )
    return {"status": "ready"}


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Order Management System (OMS)",
        "version": "1.0.0",
        "description": "Production-grade e-commerce order management backend",
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(invoice_router)
app.include_router(payment_router)
