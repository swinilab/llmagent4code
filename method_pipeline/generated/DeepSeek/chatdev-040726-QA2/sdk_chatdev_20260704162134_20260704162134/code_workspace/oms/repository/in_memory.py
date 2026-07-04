"""
In-memory repository implementations for all domain entities.
Thread-safe via a per-repository lock.
"""

import threading
from typing import Optional
from uuid import UUID

from oms.domain.models import Customer, Product, Order, Payment, Invoice


class InMemoryCustomerRepository:
    """Thread-safe in-memory store for Customer entities."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[UUID, Customer] = {}

    def save(self, customer: Customer) -> Customer:
        """Persist a customer entity (insert or update)."""
        with self._lock:
            self._store[customer.id] = customer
            return customer

    def find_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Retrieve a customer by its unique ID, or None if not found."""
        with self._lock:
            return self._store.get(customer_id)

    def find_all(self) -> list[Customer]:
        """Return all stored customer entities."""
        with self._lock:
            return list(self._store.values())

    def delete(self, customer_id: UUID) -> bool:
        """Remove a customer by ID; returns True if the entity existed."""
        with self._lock:
            return self._store.pop(customer_id, None) is not None


class InMemoryProductRepository:
    """Thread-safe in-memory store for Product entities."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[UUID, Product] = {}

    def save(self, product: Product) -> Product:
        """Persist a product entity (insert or update)."""
        with self._lock:
            self._store[product.id] = product
            return product

    def find_by_id(self, product_id: UUID) -> Optional[Product]:
        """Retrieve a product by its unique ID, or None if not found."""
        with self._lock:
            return self._store.get(product_id)

    def find_all(self) -> list[Product]:
        """Return all stored product entities."""
        with self._lock:
            return list(self._store.values())

    def delete(self, product_id: UUID) -> bool:
        """Remove a product by ID; returns True if the entity existed."""
        with self._lock:
            return self._store.pop(product_id, None) is not None


class InMemoryOrderRepository:
    """Thread-safe in-memory store for Order entities."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[UUID, Order] = {}

    def save(self, order: Order) -> Order:
        """Persist an order entity (insert or update)."""
        with self._lock:
            self._store[order.id] = order
            return order

    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        """Retrieve an order by its unique ID, or None if not found."""
        with self._lock:
            return self._store.get(order_id)

    def find_by_customer(self, customer_id: UUID) -> list[Order]:
        """Return all orders placed by a specific customer."""
        with self._lock:
            return [o for o in self._store.values() if o.customer_id == customer_id]

    def find_all(self) -> list[Order]:
        """Return all stored order entities."""
        with self._lock:
            return list(self._store.values())

    def delete(self, order_id: UUID) -> bool:
        """Remove an order by ID; returns True if the entity existed."""
        with self._lock:
            return self._store.pop(order_id, None) is not None


class InMemoryPaymentRepository:
    """Thread-safe in-memory store for Payment entities."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[UUID, Payment] = {}

    def save(self, payment: Payment) -> Payment:
        """Persist a payment entity (insert or update)."""
        with self._lock:
            self._store[payment.id] = payment
            return payment

    def find_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Retrieve a payment by its unique ID, or None if not found."""
        with self._lock:
            return self._store.get(payment_id)

    def find_by_order(self, order_id: UUID) -> list[Payment]:
        """Return all payments associated with a specific order."""
        with self._lock:
            return [p for p in self._store.values() if p.order_id == order_id]

    def find_all(self) -> list[Payment]:
        """Return all stored payment entities."""
        with self._lock:
            return list(self._store.values())

    def delete(self, payment_id: UUID) -> bool:
        """Remove a payment by ID; returns True if the entity existed."""
        with self._lock:
            return self._store.pop(payment_id, None) is not None


class InMemoryInvoiceRepository:
    """Thread-safe in-memory store for Invoice entities."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[UUID, Invoice] = {}

    def save(self, invoice: Invoice) -> Invoice:
        """Persist an invoice entity (insert or update)."""
        with self._lock:
            self._store[invoice.id] = invoice
            return invoice

    def find_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        """Retrieve an invoice by its unique ID, or None if not found."""
        with self._lock:
            return self._store.get(invoice_id)

    def find_by_order(self, order_id: UUID) -> list[Invoice]:
        """Return all invoices associated with a specific order."""
        with self._lock:
            return [i for i in self._store.values() if i.order_id == order_id]

    def find_all(self) -> list[Invoice]:
        """Return all stored invoice entities."""
        with self._lock:
            return list(self._store.values())

    def delete(self, invoice_id: UUID) -> bool:
        """Remove an invoice by ID; returns True if the entity existed."""
        with self._lock:
            return self._store.pop(invoice_id, None) is not None
