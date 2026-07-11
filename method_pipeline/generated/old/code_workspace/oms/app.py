"""
Main FastAPI application setup.

Configures the OMS API with all routers, middleware, and OpenAPI documentation.
"""
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html

from oms import __version__
from oms.config.database import init_db
from oms.controllers import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
)
from oms.models.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    await init_db()
    print("OMS Application started successfully")
    yield
    # Shutdown
    print("OMS Application shutting down")


app = FastAPI(
    title="Order Management System (OMS)",
    description="""
## Production-grade E-commerce Order Management System

A complete backend-only OMS serving three roles: **Customer**, **Order Staff**, and **Accountant**.

### Key Features
- **Customer**: Place orders, view order history, make payments
- **Order Staff**: Review orders, accept/reject, ship orders, close completed orders
- **Accountant**: Create invoices, verify payments, manage invoice status

### Order Lifecycle
1. `PENDING` → Customer places order
2. `ACCEPTED` → Order Staff reviews and accepts
3. `INVOICED` → Accountant creates invoice
4. `PAID` → Customer pays invoice (verified by Accountant)
5. `SHIPPED` → Order Staff ships the order
6. `COMPLETED` → Order Staff closes the order

### NFR Compliance
- **NFR 1.1 Response Time**: Async architecture with connection pooling
- **NFR 1.2 Concurrency**: Efficient resource utilization with async I/O
- **NFR 1.3 Queue Management**: Request handling with proper error handling
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware for production deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "details": "An unexpected error occurred. Please try again later.",
        },
    )


@app.get(
    "/",
    tags=["root"],
    summary="Root endpoint",
    description="Welcome message and API information.",
)
async def root() -> dict:
    """
    Root endpoint with API information.
    
    Returns:
        Welcome message and API version
    """
    return {
        "message": "Welcome to the Order Management System (OMS) API",
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Check API health status.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Health status with timestamp
    """
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow(),
    )


@app.get(
    "/ready",
    tags=["health"],
    summary="Readiness check",
    description="Check if API is ready to serve requests.",
)
async def readiness_check() -> dict:
    """
    Readiness check endpoint for Kubernetes probes.
    
    Returns:
        Readiness status
    """
    return {"ready": True}


# Include routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(invoice_router)


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    return app
