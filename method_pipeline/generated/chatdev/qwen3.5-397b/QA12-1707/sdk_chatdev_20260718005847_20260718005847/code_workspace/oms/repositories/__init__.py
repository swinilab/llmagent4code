"""
Repositories package for OMS data access layer.
"""

from oms.repositories.customer_repository import CustomerRepository
from oms.repositories.product_repository import ProductRepository
from oms.repositories.order_repository import OrderRepository
from oms.repositories.invoice_repository import InvoiceRepository
from oms.repositories.payment_repository import PaymentRepository

__all__ = [
    "CustomerRepository",
    "ProductRepository",
    "OrderRepository",
    "InvoiceRepository",
    "PaymentRepository",
]
