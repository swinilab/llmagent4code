"""
Controller layer for REST endpoints
"""
from .customer_controller import router as customer_router
from .product_controller import router as product_router
from .order_controller import router as order_router
from .payment_controller import router as payment_router
from .invoice_controller import router as invoice_router
from .health_controller import router as health_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "payment_router",
    "invoice_router",
    "health_router",
]
