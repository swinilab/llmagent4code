"""
Repository interfaces for OMS domain entities.
Defines abstract repository contracts for data access.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic
from app.domain.entities.models import (
    Customer, Order, Product, Payment, Invoice, OrderStatus, PaymentStatus, InvoiceStatus
)

T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """Base repository interface with common operations."""

    @abstractmethod
    def save(self, entity: T) -> T:
        """Persist entity and return saved instance."""
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID."""
        pass

    @abstractmethod
    def find_all(self) -> List[T]:
        """Retrieve all entities."""
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID. Returns True if deleted."""
        pass

    @abstractmethod
    def update(self, entity_id: str, data: dict) -> Optional[T]:
        """Update entity fields and return updated entity."""
        pass


class CustomerRepository(Repository[Customer]):
    """Repository interface for Customer entities."""

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[Customer]:
        """Find customer by email address."""

    @abstractmethod
    def find_by_role(self, role: str) -> List[Customer]:
        """Find all customers with specific role."""

    @abstractmethod
    def find_active(self) -> List[Customer]:
        """Find all active customers."""


class OrderRepository(Repository[Order]):
    """Repository interface for Order entities."""

    @abstractmethod
    def find_by_customer(self, customer_id: str) -> List[Order]:
        """Find all orders for a customer."""

    @abstractmethod
    def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find all orders with specific status."""

    @abstractmethod
    def find_pending_orders(self) -> List[Order]:
        """Find all pending orders awaiting review."""

    @abstractmethod
    def find_by_invoice_id(self, invoice_id: str) -> Optional[Order]:
        """Find order by associated invoice ID."""


class ProductRepository(Repository[Product]):
    """Repository interface for Product entities."""

    @abstractmethod
    def find_by_sku(self, sku: str) -> Optional[Product]:
        """Find product by SKU."""

    @abstractmethod
    def find_by_category(self, category: str) -> List[Product]:
        """Find all products in a category."""

    @abstractmethod
    def find_active(self) -> List[Product]:
        """Find all active products."""

    @abstractmethod
    def search(self, query: str) -> List[Product]:
        """Search products by name or description."""


class PaymentRepository(Repository[Payment]):
    """Repository interface for Payment entities."""

    @abstractmethod
    def find_by_order(self, order_id: str) -> List[Payment]:
        """Find all payments for an order."""

    @abstractmethod
    def find_by_status(self, status: PaymentStatus) -> List[Payment]:
        """Find all payments with specific status."""

    @abstractmethod
    def find_by_transaction_ref(self, ref: str) -> Optional[Payment]:
        """Find payment by transaction reference."""


class InvoiceRepository(Repository[Invoice]):
    """Repository interface for Invoice entities."""

    @abstractmethod
    def find_by_order(self, order_id: str) -> Optional[Invoice]:
        """Find invoice for an order."""

    @abstractmethod
    def find_by_status(self, status: InvoiceStatus) -> List[Invoice]:
        """Find all invoices with specific status."""

    @abstractmethod
    def find_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Find invoice by invoice number."""

    @abstractmethod
    def find_overdue(self) -> List[Invoice]:
        """Find all overdue invoices."""

    @abstractmethod
    def find_by_customer(self, customer_id: str) -> List[Invoice]:
        """Find all invoices for a customer."""
