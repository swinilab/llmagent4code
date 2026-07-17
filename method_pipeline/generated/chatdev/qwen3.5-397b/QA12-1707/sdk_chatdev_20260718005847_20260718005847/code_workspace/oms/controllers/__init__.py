"""
Controllers package for OMS REST API endpoints.
"""

from oms.controllers.customer_controller import customer_router
from oms.controllers.product_controller import product_router
from oms.controllers.order_controller import order_router
from oms.controllers.invoice_controller import invoice_router
from oms.controllers.payment_controller import payment_router

__all__ = [
    "customer_router",
    "product_router",
    "order_router",
    "invoice_router",
    "payment_router",
]
