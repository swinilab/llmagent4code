"""
FastAPI application entrypoint.
"""
from fastapi import FastAPI
from app.controllers import customer, order, product, payment, invoice
from app.middleware.logging import log_requests
from app.middleware.recovery import graceful_degradation_middleware
from app.core.config import settings
from app.tasks.celery_app import celery_app
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.JSONRenderer()
    ]
)

app = FastAPI(title="Order Management System")

# Middleware
app.middleware("http")(log_requests)
app.middleware("http")(graceful_degradation_middleware)

# Routers
app.include_router(customer.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(order.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(product.router, prefix="/api/v1/products", tags=["products"])
app.include_router(payment.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(invoice.router, prefix="/api/v1/invoices", tags=["invoices"])

@app.on_event("startup")
def startup_event():
    """Trigger recovery on startup using Celery to avoid blocking."""
    celery_app.send_task("app.tasks.recovery_tasks.recover_pending_operations")