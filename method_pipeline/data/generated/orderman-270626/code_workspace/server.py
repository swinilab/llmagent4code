"""
Main server module for the Order Management System.
Sets up FastAPI application with all routes and middleware.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database.models import init_db
from database.config import FEATURE_FLAGS, CACHE_EXPIRATION_SECONDS
from routes import (
    customer_router,
    product_router,
    order_router,
    invoice_router,
    payment_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Handles database initialization and cleanup.
    """
    # Startup
    logger.info("Starting Order Management System...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
        
        # Seed initial data if database is empty
        await seed_initial_data()
        logger.info("Initial data seeded successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    from database.models import dispose_engine
    await dispose_engine()
    logger.info("Database connections closed")
    logger.info("Shutting down Order Management System...")

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Order Management System",
        description="A comprehensive order management system handling customer orders, payment processing, and shipping.",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom exception handler for graceful degradation
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Global exception handler for graceful error handling.
        Implements NFR 3.1 (Graceful Degradation) and NFR 3.2 (Fault Detection).
        """
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        # Check if we should degrade non-essential features
        if FEATURE_FLAGS.get("enable_heavy_logging"):
            logger.error(f"Request details: {request.method} {request.url}")
        
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Internal server error", "detail": str(exc)},
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent response format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.detail},
        )
    
    # Include routers
    app.include_router(customer_router)
    app.include_router(product_router)
    app.include_router(order_router)
    app.include_router(invoice_router)
    app.include_router(payment_router)
    
    # Mount static files for frontend
    if os.path.exists("frontend"):
        app.mount("/static", StaticFiles(directory="frontend"), name="static")
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """
        Health check endpoint for monitoring and fault detection.
        Implements NFR 3.2 (Fault Detection and Recovery).
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "features": FEATURE_FLAGS,
            "cache_expiration": CACHE_EXPIRATION_SECONDS,
        }
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """
        Root endpoint serving the frontend application.
        """
        if os.path.exists("frontend/index.html"):
            return FileResponse("frontend/index.html")
        return {
            "message": "Order Management System API",
            "docs": "/docs",
            "health": "/health",
        }
    
    return app


async def seed_initial_data():
    """
    Seed initial data for demonstration purposes.
    Creates sample customers, products for testing the workflow.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from database.models import get_session_factory, CustomerModel, ProductModel, UserRoleEnum
    from sqlalchemy import select, func
    
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        # Check if data already exists
        result = await session.execute(select(func.count()).select_from(CustomerModel))
        customer_count = result.scalar()
        
        if customer_count == 0:
            # Create sample customers
            customers = [
                CustomerModel(
                    name="John Doe",
                    address="123 Main St, City, State 12345",
                    phone="555-0101",
                    email="john.doe@example.com",
                    banking_details="Bank of America - ****1234",
                    role=UserRoleEnum.CUSTOMER,
                ),
                CustomerModel(
                    name="Jane Smith",
                    address="456 Oak Ave, Town, State 67890",
                    phone="555-0102",
                    email="jane.smith@example.com",
                    banking_details="Chase Bank - ****5678",
                    role=UserRoleEnum.CUSTOMER,
                ),
                CustomerModel(
                    name="Order Staff User",
                    address="789 Company Blvd, Business, State 11111",
                    phone="555-0103",
                    email="staff@company.com",
                    banking_details=None,
                    role=UserRoleEnum.ORDER_STAFF,
                ),
                CustomerModel(
                    name="Accountant User",
                    address="321 Finance St, Money, State 22222",
                    phone="555-0104",
                    email="accountant@company.com",
                    banking_details=None,
                    role=UserRoleEnum.ACCOUNTANT,
                ),
            ]
            
            for customer in customers:
                session.add(customer)
            
            # Create sample products
            products = [
                ProductModel(
                    name="Laptop Pro 15",
                    description="High-performance laptop with 15-inch display, 16GB RAM, 512GB SSD",
                    price=1299.99,
                    sku="LAPTOP-PRO-15",
                    stock_quantity=50,
                ),
                ProductModel(
                    name="Wireless Mouse",
                    description="Ergonomic wireless mouse with long battery life",
                    price=49.99,
                    sku="MOUSE-WL-001",
                    stock_quantity=200,
                ),
                ProductModel(
                    name="Mechanical Keyboard",
                    description="RGB mechanical keyboard with Cherry MX switches",
                    price=149.99,
                    sku="KEYBOARD-MECH-RGB",
                    stock_quantity=100,
                ),
                ProductModel(
                    name="USB-C Hub",
                    description="7-in-1 USB-C hub with HDMI, USB 3.0, and SD card reader",
                    price=79.99,
                    sku="HUB-USBC-7IN1",
                    stock_quantity=150,
                ),
                ProductModel(
                    name="Monitor 27 inch",
                    description="27-inch 4K UHD monitor with HDR support",
                    price=399.99,
                    sku="MONITOR-27-4K",
                    stock_quantity=30,
                ),
            ]
            
            for product in products:
                session.add(product)
            
            await session.commit()
            logger.info("Seeded 4 customers and 5 products")


# Create the application instance
app = create_app()


def run():
    """
    Run the server using uvicorn.
    This is the main entry point for the application.
    """
    import uvicorn
    
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run()
