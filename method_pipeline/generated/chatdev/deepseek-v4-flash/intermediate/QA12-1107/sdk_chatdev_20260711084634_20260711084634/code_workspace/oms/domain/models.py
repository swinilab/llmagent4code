"""
Pure domain models for the Order Management System.
These contain business logic and state transition validation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import ClassVar, List, Optional

from oms.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from oms.domain.exceptions import (
    InvalidStateTransitionError,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Money:
    """Immutable money value object."""
    amount: Decimal
    currency: str = "USD"

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: int) -> Money:
        return Money(self.amount * factor, self.currency)


@dataclass(frozen=True)
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str


@dataclass(frozen=True)
class BankingDetails:
    account_holder: str
    account_number: str
    routing_number: str
    bank_name: str


@dataclass(frozen=True)
class LineItem:
    product_id: str
    product_name: str
    quantity: int
    unit_price: Money

    @property
    def total_price(self) -> Money:
        return self.unit_price * self.quantity


# ---------------------------------------------------------------------------
# Domain Entities
# ---------------------------------------------------------------------------


@dataclass
class Customer:
    id: str = field(default_factory=_new_id)
    name: str = ""
    address: Optional[Address] = None
    phone: str = ""
    banking_details: Optional[BankingDetails] = None
    order_history: List[str] = field(default_factory=list)
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1


@dataclass
class Product:
    id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    base_price: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    stock: int = 0
    available: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1


@dataclass
class Order:
    id: str = field(default_factory=_new_id)
    customer_id: str = ""
    line_items: List[LineItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    invoice_ref: Optional[str] = None
    payment_ref: Optional[str] = None
    shipping_address: Optional[Address] = None
    notes: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1

    # Allowed state transitions (class variable, not a dataclass field)
    _ALLOWED_TRANSITIONS: ClassVar[dict] = {
        OrderStatus.CREATED: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
        OrderStatus.ACCEPTED: {OrderStatus.INVOICED, OrderStatus.CANCELLED},
        OrderStatus.INVOICED: {OrderStatus.PAID, OrderStatus.CANCELLED},
        OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
        OrderStatus.SHIPPED: {OrderStatus.CLOSED},
        OrderStatus.CLOSED: set(),
        OrderStatus.CANCELLED: set(),
    }

    def transition_to(self, new_status: OrderStatus) -> None:
        """Validate and apply a state transition.

        This method enforces the domain state machine. It is called
        *before* the service layer persists the new state to the
        database, so the domain object is mutated in-memory first,
        then the updated version is flushed to the DB.
        """
        allowed = self._ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(self.status.value, new_status.value)
        self.status = new_status
        self.updated_at = _utcnow()

    def recalculate_total(self) -> None:
        """Recalculate total_amount from line items."""
        total = Money(Decimal("0.00"))
        for item in self.line_items:
            total = total + item.total_price
        self.total_amount = total


@dataclass
class Payment:
    id: str = field(default_factory=_new_id)
    order_id: str = ""
    amount: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    transaction_id: str = ""
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1


@dataclass
class Invoice:
    id: str = field(default_factory=_new_id)
    order_id: str = ""
    customer_id: str = ""
    billing_address: Optional[Address] = None
    line_items: List[LineItem] = field(default_factory=list)
    subtotal: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    tax: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    total: Money = field(default_factory=lambda: Money(Decimal("0.00")))
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    version: int = 1
