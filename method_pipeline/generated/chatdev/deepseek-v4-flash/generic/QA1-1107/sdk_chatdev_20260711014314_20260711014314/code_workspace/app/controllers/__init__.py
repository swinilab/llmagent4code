"""Controllers (REST API routers) package."""
from app.controllers.customer_controller import router as customer_router
from app.controllers.product_controller import router as product_router
from app.controllers.order_controller import router as order_router
from app.controllers.payment_controller import router as payment_router
from app.controllers.invoice_controller import router as invoice_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "payment_router",
    "invoice_router",
]
