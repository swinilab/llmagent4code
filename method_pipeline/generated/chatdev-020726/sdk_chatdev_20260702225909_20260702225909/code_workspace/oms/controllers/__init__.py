"""
Controllers package initialization.

Contains FastAPI routers for all API endpoints.
"""
from oms.controllers.customer_controller import router as customer_router
from oms.controllers.product_controller import router as product_router
from oms.controllers.order_controller import router as order_router
from oms.controllers.payment_controller import router as payment_router
from oms.controllers.invoice_controller import router as invoice_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "payment_router",
    "invoice_router",
]
