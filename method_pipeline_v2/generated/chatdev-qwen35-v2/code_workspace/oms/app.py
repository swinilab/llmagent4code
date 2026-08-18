"""
FastAPI application factory for OMS
Implements NFR 2.1 Exception Detection, NFR 2.2 Graceful Degradation
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from oms.controller import (
    customer_router, product_router, order_router,
    payment_router, invoice_router
)
from oms.infrastructure.exceptions import (
    oms_exception_handler, validation_exception_handler,
    sqlalchemy_exception_handler, generic_exception_handler,
    OMSException
)
from sqlalchemy.exc import SQLAlchemyError

def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    """
    app = FastAPI(
        title="Order Management System (OMS)",
        description="Production-grade backend-only e-commerce Order Management System",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(customer_router)
    app.include_router(product_router)
    app.include_router(order_router)
    app.include_router(payment_router)
    app.include_router(invoice_router)
    
    # Register exception handlers (NFR 2.1, NFR 2.2)
    app.add_exception_handler(OMSException, oms_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    return app

app = create_app()
