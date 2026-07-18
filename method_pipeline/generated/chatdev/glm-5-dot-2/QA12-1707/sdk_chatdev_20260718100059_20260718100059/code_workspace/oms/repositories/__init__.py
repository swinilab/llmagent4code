"""Repository layer — data access for all entities."""
from oms.repositories.base import BaseRepository
from oms.repositories.customer import CustomerRepository
from oms.repositories.product import ProductRepository
from oms.repositories.order import OrderRepository
from oms.repositories.payment import PaymentRepository
from oms.repositories.invoice import InvoiceRepository

__all__ = [
    "BaseRepository",
    "CustomerRepository",
    "ProductRepository",
    "OrderRepository",
    "PaymentRepository",
    "InvoiceRepository",
]