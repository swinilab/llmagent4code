"""
Main server module
FastAPI application setup with routing and middleware
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from oms_backend.config import settings
from oms_backend.controller import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
)
from oms_backend.utils.exceptions import OMSException
from oms_backend.infrastructure.database import engine
from oms_backend.repository.models import Base


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Order Management System (OMS) - Production-grade e-commerce backend",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handler for OMS exceptions
    @app.exception_handler(OMSException)
    async def oms_exception_handler(request: Request, exc: OMSException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if settings.debug:
            raise exc
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error",
                "details": {"type": type(exc).__name__},
            },
        )
    
    # Include routers with versioned paths
    app.include_router(customer_router, prefix="/api/v1")
    app.include_router(product_router, prefix="/api/v1")
    app.include_router(order_router, prefix="/api/v1")
    app.include_router(payment_router, prefix="/api/v1")
    app.include_router(invoice_router, prefix="/api/v1")
    
    @app.get("/health", tags=["health"])
    def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "version": settings.app_version}
    
    @app.get("/", tags=["root"])
    def root():
        """Root endpoint"""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/api/docs",
        }
    
    return app


# Create the application instance
app = create_app()


def run():
    """
    Run the server.
    Entry point for starting the application.
    """
    import uvicorn
    uvicorn.run(
        "oms_backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
