"""
Domain models for the Order Management System.
These are plain Python objects (not ORM models) representing the core business entities.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from .enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Customer:
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: str  # "CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"
    order_history: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class Product:
    id: str
    description: str
    base_price: Decimal
    currency: str = "USD"
    stock_available: bool = True
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class OrderLineItem:
    product_id: str
    product_description: str
    quantity: int
    unit_price: Decimal
    currency: str = "USD"

    @property
    def total_price(self) -> Decimal:
        return self.unit_price * Decimal(self.quantity)


@dataclass
class Order:
    id: str
    customer_id: str
    line_items: list[OrderLineItem]
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    invoice_ref: Optional[str] = None
    version: int = 1  # Optimistic lock field
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self):
        if self.total_amount == Decimal("0.00") and self.line_items:
            self._recalculate_total()

    def _recalculate_total(self) -> None:
        self.total_amount = sum(
            (item.unit_price * Decimal(item.quantity))
            for item in self.line_items
        )

    def transition_to(self, target_status: OrderStatus) -> None:
        """Enforce state transition at the domain layer."""
        if not self.status.can_transition_to(target_status):
            from .errors import InvalidStateTransitionError
            raise InvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target_status.value,
            )
        self.status = target_status
        self.updated_at = _utcnow()

    def add_line_item(self, product: "Product", quantity: int) -> None:
        if self.status != OrderStatus.CREATED:
            from .errors import BusinessRuleViolationError
            raise BusinessRuleViolationError(
                "Cannot modify line items after order is accepted"
            )
        item = OrderLineItem(
            product_id=product.id,
            product_description=product.description,
            quantity=quantity,
            unit_price=product.base_price,
            currency=product.currency,
        )
        self.line_items.append(item)
        self._recalculate_total()
        self.updated_at = _utcnow()


@dataclass
class Payment:
    id: str
    order_id: str
    amount: Decimal
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    status: PaymentStatus = PaymentStatus.PENDING
    timestamp: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class Invoice:
    id: str
    order_id: str
    billing_name: str
    billing_address: str
    total_amount: Decimal
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
