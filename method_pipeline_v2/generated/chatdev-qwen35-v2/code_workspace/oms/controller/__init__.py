"""
Controller module for OMS
"""
from oms.controller.customer_controller import customer_router
from oms.controller.product_controller import product_router
from oms.controller.order_controller import order_router
from oms.controller.payment_controller import payment_router
from oms.controller.invoice_controller import invoice_router

__all__ = [
    'customer_router', 'product_router', 'order_router',
    'payment_router', 'invoice_router'
]
