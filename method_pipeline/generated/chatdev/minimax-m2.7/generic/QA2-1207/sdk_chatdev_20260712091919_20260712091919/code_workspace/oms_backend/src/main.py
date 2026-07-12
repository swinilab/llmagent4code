"""
OMS Backend - Main Application Entry Point
FastAPI application with all routers configured.
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .controllers import (
    customer_router,
    product_router,
    order_router,
    invoice_router,
    payment_router,
    health_router
)
from .infrastructure.database import init_db, check_db_health, SessionLocal
from .services.order_service import OrderService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    logger.info("Starting OMS Backend...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Check database health
    db_health = check_db_health()
    logger.info(f"Database health: {db_health}")
    
    # Recover any pending orders from previous crash
    try:
        db = SessionLocal()
        order_service = OrderService(db)
        recovered = order_service.recover_pending_orders()
        if recovered:
            logger.info(f"Recovered {len(recovered)} pending orders from previous session")
        db.close()
    except Exception as e:
        logger.warning(f"Could not recover pending orders: {e}")
    
    logger.info("OMS Backend started successfully")
    
    yield
    
    logger.info("Shutting down OMS Backend...")


app = FastAPI(
    title="Order Management System API",
    description="""
## OMS Backend API

A production-grade Order Management System backend implementing the complete order workflow:

1. **Customer places order** - `POST /api/v1/orders`
2. **Order Staff reviews & accepts** - `PATCH /api/v1/orders/{id}/accept`
3. **Accountant creates invoice** - `POST /api/v1/invoices`
4. **Customer pays invoice** - `POST /api/v1/payments`
5. **Accountant verifies payment** - `POST /api/v1/payments/{id}/verify`
6. **Order Staff ships paid order** - `PATCH /api/v1/orders/{id}/ship`
7. **Order Staff closes completed order** - `PATCH /api/v1/orders/{id}/close`

## NFR Support

- **NFR 2.1 Graceful Degradation**: Feature flags and circuit breakers
- **NFR 2.2 Fault Detection**: Health checks and automatic recovery
- **NFR 2.3 State Preservation**: WAL mode, snapshots, and idempotency keys
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Include all routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(invoice_router)
app.include_router(payment_router)
app.include_router(health_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "OMS Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


def run():
    """Run the application using uvicorn."""
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    run()
