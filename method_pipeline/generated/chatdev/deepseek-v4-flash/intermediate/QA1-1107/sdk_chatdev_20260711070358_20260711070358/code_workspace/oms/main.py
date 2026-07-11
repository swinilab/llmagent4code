"""
Main application entry point for the Order Management System.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oms.config import settings
from oms.infrastructure.database import database, init_db
from oms.infrastructure.cache import cache
from oms.infrastructure.task_queue import task_queue
from oms.infrastructure.rate_limiter import rate_limiter
from oms.infrastructure.logging import setup_logging, get_logger
from oms.api.routes import router, add_correlation_id, domain_error_handler
from oms.domain.errors import DomainError

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and clean up resources."""
    setup_logging()
    logger.info("Starting Order Management System")

    # Initialize infrastructure
    await init_db()
    await cache.initialize()
    await task_queue.initialize()

    logger.info(
        "Infrastructure initialized",
        extra={
            "database_pool_size": settings.database_pool_size,
            "redis_pool_size": settings.redis_pool_size,
            "rate_limit_capacity": settings.rate_limit_tokens,
            "rate_limit_refill": settings.rate_limit_refill_rate,
        },
    )

    yield

    # Cleanup
    await database.close()
    await cache.close()
    await task_queue.close()
    logger.info("Order Management System shut down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Production-grade e-commerce Order Management System",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware
    app.middleware("http")(add_correlation_id)

    # Domain error handler
    app.add_exception_handler(DomainError, domain_error_handler)

    # Include API routes
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "oms.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        # Use uvloop for async performance
        loop="uvloop",
        # HTTP tools for faster parsing
        http="httptools",
    )
