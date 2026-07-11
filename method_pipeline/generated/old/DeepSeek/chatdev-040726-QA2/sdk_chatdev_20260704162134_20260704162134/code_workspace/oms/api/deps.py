"""
Dependency injection for FastAPI.
Provides singleton instances of repositories and services.
"""

from oms.repository.in_memory import (
    InMemoryCustomerRepository,
    InMemoryProductRepository,
    InMemoryOrderRepository,
    InMemoryPaymentRepository,
    InMemoryInvoiceRepository,
)
from oms.service.customer_service import CustomerService
from oms.service.product_service import ProductService
from oms.service.order_service import OrderService
from oms.service.invoice_service import InvoiceService
from oms.service.payment_service import PaymentService

# ---------------------------------------------------------------------------
# Singleton repositories
# ---------------------------------------------------------------------------
_customer_repo = InMemoryCustomerRepository()
_product_repo = InMemoryProductRepository()
_order_repo = InMemoryOrderRepository()
_payment_repo = InMemoryPaymentRepository()
_invoice_repo = InMemoryInvoiceRepository()

# ---------------------------------------------------------------------------
# Singleton services
# ---------------------------------------------------------------------------
_customer_service = CustomerService(_customer_repo)
_product_service = ProductService(_product_repo)
_order_service = OrderService(_order_repo, _customer_repo, _product_repo)
_invoice_service = InvoiceService(_invoice_repo, _order_repo)
_payment_service = PaymentService(_payment_repo, _order_repo, _invoice_repo)


def get_customer_service() -> CustomerService:
    return _customer_service


def get_product_service() -> ProductService:
    return _product_service


def get_order_service() -> OrderService:
    return _order_service


def get_invoice_service() -> InvoiceService:
    return _invoice_service


def get_payment_service() -> PaymentService:
    return _payment_service
