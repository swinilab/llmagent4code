"""
Main FastAPI application server
Sets up routing, middleware, and lifecycle events
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import json

from oms_backend.config.settings import get_settings
from oms_backend.repository.base import db
from oms_backend.controller import (
    customer_router,
    product_router,
    order_router,
    payment_router,
    invoice_router,
)
from oms_backend.infrastructure.rate_limiter import rate_limiter
from oms_backend.infrastructure.fault_injection import fault_injector
from oms_backend.infrastructure.state_sync import state_synchronizer

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events"""
    # Startup
    await db.init_db()
    state_synchronizer.start()
    
    yield
    
    # Shutdown
    state_synchronizer.stop()
    await db.close()


app = FastAPI(
    title="Order Management System (OMS)",
    description="Production-grade e-commerce order management backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for NFR 1.1"""
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.allow_request(client_ip):
        return Response(
            content=json.dumps({"detail": "Rate limit exceeded"}),
            status_code=429,
            media_type="application/json"
        )
    
    response = await call_next(request)
    return response


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Request timing middleware for monitoring"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(customer_router)
app.include_router(product_router)
app.include_router(order_router)
app.include_router(payment_router)
app.include_router(invoice_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/nfr-stats")
async def nfr_stats():
    """Get NFR-related statistics"""
    return {
        "rate_limiter": {
            "max_rate": settings.max_events_per_second,
        },
        "state_sync": state_synchronizer.get_stats(),
        "fault_injection": {
            "enabled": fault_injector.enabled,
            "active": fault_injector.is_fault_active(),
        }
    }


def run():
    """Run the server"""
    import uvicorn
    uvicorn.run(
        "oms_backend.server:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )


if __name__ == "__main__":
    run()
