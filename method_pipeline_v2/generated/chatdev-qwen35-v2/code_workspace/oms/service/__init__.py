"""
Service module for OMS
"""
from oms.service.customer_service import CustomerService
from oms.service.product_service import ProductService
from oms.service.order_service import OrderService
from oms.service.payment_service import PaymentService
from oms.service.invoice_service import InvoiceService

__all__ = [
    'CustomerService', 'ProductService', 'OrderService',
    'PaymentService', 'InvoiceService'
]
