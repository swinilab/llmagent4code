"""
Shared domain models - pure dataclasses used across all layers.
These represent the ubiquitous language of the OMS domain.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4


def utcnow() -> datetime:
    """Return current UTC datetime (replacement for deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc)


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    PAYPAL = "PAYPAL"
    CASH = "CASH"


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


@dataclass
class Customer:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    address: str = ""
    phone: str = ""
    banking_details: str = ""
    role: UserRole = UserRole.CUSTOMER
    order_history: list[UUID] = field(default_factory=list)


@dataclass
class Product:
    id: UUID = field(default_factory=uuid4)
    description: str = ""
    base_price: Decimal = Decimal("0.00")
    currency: str = "USD"


@dataclass
class LineItem:
    product_id: UUID
    id: UUID = field(default_factory=uuid4)
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")
    currency: str = "USD"

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    line_items: list[LineItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    invoice_id: Optional[UUID] = None
    payment_id: Optional[UUID] = None

    @property
    def total_amount(self) -> Decimal:
        return sum((item.total for item in self.line_items), Decimal("0.00"))


@dataclass
class Payment:
    id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    status: PaymentStatus = PaymentStatus.PENDING
    timestamp: datetime = field(default_factory=utcnow)


@dataclass
class Invoice:
    id: UUID = field(default_factory=uuid4)
    order_id: UUID = field(default_factory=uuid4)
    billing_name: str = ""
    billing_address: str = ""
    total_amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    issue_date: datetime = field(default_factory=utcnow)
    due_date: datetime = field(default_factory=utcnow)
    status: InvoiceStatus = InvoiceStatus.DRAFT
