"""
Main FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.connection_pool import init_db, close_db
from app.queue.queue_manager import get_queue_manager
from app.controllers import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
    health_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await init_db()
    queue_manager = get_queue_manager()
    await queue_manager.start_workers()
    yield
    # Shutdown
    await queue_manager.stop_workers()
    await close_db()


app = FastAPI(
    title="Order Management System (OMS)",
    description="Production-grade backend-only e-commerce Order Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(invoice_router)
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Order Management System",
        "version": "1.0.0",
        "status": "running",
    }
