"""
Repository module for OMS
"""
from oms.repository.customer_repository import CustomerRepository
from oms.repository.product_repository import ProductRepository
from oms.repository.order_repository import OrderRepository
from oms.repository.payment_repository import PaymentRepository
from oms.repository.invoice_repository import InvoiceRepository

__all__ = [
    'CustomerRepository', 'ProductRepository', 'OrderRepository',
    'PaymentRepository', 'InvoiceRepository'
]
