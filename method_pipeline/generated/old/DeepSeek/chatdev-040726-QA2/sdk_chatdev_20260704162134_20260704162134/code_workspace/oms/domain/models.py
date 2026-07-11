"""
Shared domain models used across the entire system.
"""

from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from oms.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentStatus,
    PaymentMethod,
    Currency,
    UserRole,
)


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class Money(BaseModel):
    """Monetary value with currency. Amount is always rounded to 2 decimal places."""
    amount: Decimal = Field(..., ge=0)
    currency: Currency = Currency.USD

    @field_validator("amount", mode="before")
    @classmethod
    def round_to_two_places(cls, v: Decimal) -> Decimal:
        """Ensure monetary amounts are always rounded to 2 decimal places."""
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add Money with different currencies")
        result = (self.amount + other.amount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return Money(amount=result, currency=self.currency)


class Address(BaseModel):
    """Physical address value object."""
    street: str
    city: str
    state: str
    zip_code: str
    country: str


class BankingDetails(BaseModel):
    """Banking information value object."""
    bank_name: str
    account_number: str
    routing_number: str


class LineItem(BaseModel):
    """A single line item on an order."""
    product_id: UUID
    product_description: str
    quantity: int = Field(..., ge=1)
    unit_price: Money


# ---------------------------------------------------------------------------
# Entity Models
# ---------------------------------------------------------------------------


class Customer(BaseModel):
    """Customer entity."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    address: Address
    phone: str
    banking_details: BankingDetails
    order_history: list[UUID] = Field(default_factory=list)
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Product(BaseModel):
    """Product entity."""
    id: UUID = Field(default_factory=uuid4)
    description: str
    base_price: Money
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Order(BaseModel):
    """Order entity with full lifecycle status."""
    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    line_items: list[LineItem]
    total: Money
    status: OrderStatus = OrderStatus.PENDING
    invoice_ref: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Payment(BaseModel):
    """Payment entity."""
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    invoice_id: UUID
    amount: Money
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod
    verified_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Invoice(BaseModel):
    """Invoice entity."""
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    customer_id: UUID
    billing_address: Address
    line_items: list[LineItem]
    subtotal: Money
    tax: Money = Field(default_factory=lambda: Money(amount=Decimal("0.00"), currency=Currency.USD))
    total: Money
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------


class CreateOrderRequest(BaseModel):
    """Request body for placing a new order."""
    customer_id: UUID
    line_items: list[LineItem]


class CreatePaymentRequest(BaseModel):
    """Request body for making a payment."""
    order_id: UUID
    invoice_id: UUID
    amount: Money
    method: PaymentMethod


class CreateInvoiceRequest(BaseModel):
    """Request body for creating an invoice."""
    order_id: UUID
    customer_id: UUID
    billing_address: Address
    tax: Money = Field(default_factory=lambda: Money(amount=Decimal("0.00"), currency=Currency.USD))
    due_date: date


class CreateCustomerRequest(BaseModel):
    """Request body for registering a customer."""
    name: str
    address: Address
    phone: str
    banking_details: BankingDetails


class CreateProductRequest(BaseModel):
    """Request body for creating a product."""
    description: str
    base_price: Money


class StaffActionRequest(BaseModel):
    """Request body for staff actions (accept, ship, close)."""
    staff_id: UUID


class AccountantActionRequest(BaseModel):
    """Request body for accountant actions (verify)."""
    accountant_id: UUID


class CancelOrderRequest(BaseModel):
    """Request body for cancelling an order."""
    reason: str = "Cancelled by customer"
