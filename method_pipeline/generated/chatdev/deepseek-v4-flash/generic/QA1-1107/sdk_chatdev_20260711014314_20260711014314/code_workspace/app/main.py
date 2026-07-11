"""
FastAPI application entry point for the Order Management System.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.tasks.background import get_task_processor
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_logger import RequestLoggingMiddleware
from app.controllers import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting Order Management System...")
    # Initialize database tables
    await init_db()
    logger.info("Database tables created/verified")

    # Start background task processor
    processor = get_task_processor()
    await processor.start()

    yield

    # Shutdown
    await processor.stop()
    logger.info("Order Management System shut down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade Order Management System backend API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS (allow all origins for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters: rate limiter before request logger)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Register routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(invoice_router)

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="OMS Backend Server")
    parser.add_argument("--host", type=str, default=settings.host, help="Bind address")
    parser.add_argument("--port", type=int, default=settings.port, help="Bind port")
    parser.add_argument("--workers", type=int, default=settings.workers, help="Number of workers")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level="info",
    )
