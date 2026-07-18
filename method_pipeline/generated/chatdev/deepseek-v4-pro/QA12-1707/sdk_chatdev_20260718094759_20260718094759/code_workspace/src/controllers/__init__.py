"""Controllers package — REST API routers."""

from src.controllers.customer import router as customer_router
from src.controllers.invoice import router as invoice_router
from src.controllers.order import router as order_router
from src.controllers.payment import router as payment_router
from src.controllers.product import router as product_router
from src.controllers.workflow import router as workflow_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "payment_router",
    "invoice_router",
    "workflow_router",
]
