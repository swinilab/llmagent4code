"""
Routes module for the Order Management System.
Defines API endpoints and HTTP methods.
"""
from routes.customer_routes import router as customer_router
from routes.product_routes import router as product_router
from routes.order_routes import router as order_router
from routes.invoice_routes import router as invoice_router
from routes.payment_routes import router as payment_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "invoice_router",
    "payment_router",
]
