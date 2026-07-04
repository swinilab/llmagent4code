"""
Convenience imports for all routers.
"""
from app.routers.customer_router import router as customer_router
from app.routers.product_router import router as product_router
from app.routers.order_router import router as order_router
from app.routers.payment_router import router as payment_router
from app.routers.invoice_router import router as invoice_router
from app.routers.workflow_router import router as workflow_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "payment_router",
    "invoice_router",
    "workflow_router",
]
