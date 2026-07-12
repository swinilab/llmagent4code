"""
Pydantic v2 domain models (schemas) shared between API and service layers.
Uses discriminated unions and nested models for full lifecycle coverage.

ADR-003: Pydantic v2 chosen for 50× validation speed vs v1.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    PENDING    = "pending"
    ACCEPTED   = "accepted"
    INVOICED   = "invoiced"
    PAID       = "paid"
    SHIPPED    = "shipped"
    DELIVERED  = "delivered"
    CLOSED     = "closed"
    CANCELLED  = "cancelled"


class InvoiceStatus(str, Enum):
    DRAFT      = "draft"
    ISSUED     = "issued"
    PAID       = "paid"
    OVERDUE    = "overdue"
    CANCELLED  = "cancelled"


class PaymentStatus(str, Enum):
    PENDING     = "pending"
    AUTHORIZED  = "authorized"
    CAPTURED    = "captured"
    FAILED      = "failed"
    REFUNDED    = "refunded"


class UserRole(str, Enum):
    CUSTOMER    = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT  = "accountant"


# ─────────────────────────────────────────────────────────────────────────────
# Shared / Scalar models
# ─────────────────────────────────────────────────────────────────────────────

class Money(BaseModel):
    """Monetary amount with currency. Immutable."""
    amount: Annotated[Decimal, Field(ge=0, decimal_places=4)] = Field(default=Decimal("0"))
    currency: str = Field(default="USD", max_length=3)

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} != {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __mul__(self, quantity: int) -> Money:
        return Money(amount=self.amount * Decimal(quantity), currency=self.currency)


class Address(BaseModel):
    model_config = ConfigDict(frozen=True)
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


# ─────────────────────────────────────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    address: Address = Field(default_factory=Address)
    role: UserRole = UserRole.CUSTOMER
    bank_name: str | None = None
    bank_account: str | None = None
    bank_routing: str | None = None

    @field_validator("email")
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    address: Address | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_routing: str | None = None


class Customer(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    base_price: Decimal = Field(gt=0, decimal_places=4)
    currency: str = Field(default="USD", max_length=3)
    stock_qty: int = Field(ge=0, default=0)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    base_price: Decimal | None = Field(default=None, gt=0, decimal_places=4)
    stock_qty: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProductSearchResult(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    base_price: Decimal
    currency: str


# ─────────────────────────────────────────────────────────────────────────────
# Line Item
# ─────────────────────────────────────────────────────────────────────────────

class LineItemCreate(BaseModel):
    """Input schema for creating a line item (used in order creation)."""
    product_id: uuid.UUID
    quantity: Annotated[int, Field(gt=0)]
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=4)

    @computed_field
    @property
    def line_total(self) -> Decimal:
        return Decimal("0")  # overridden at service layer with unit_price


class LineItem(BaseModel):
    """Output schema for a persisted line item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Order
# ─────────────────────────────────────────────────────────────────────────────

class OrderBase(BaseModel):
    notes: str | None = None


class OrderCreate(OrderBase):
    customer_id: uuid.UUID
    items: list[LineItemCreate] = Field(min_length=1)
    # Flat shipping address fields — mirror ORM columns exactly
    ship_address: str | None = None
    ship_city: str | None = None
    ship_state: str | None = None
    ship_postal: str | None = None
    ship_country: str | None = None


class OrderUpdate(BaseModel):
    ship_address: str | None = None
    ship_city: str | None = None
    ship_state: str | None = None
    ship_postal: str | None = None
    ship_country: str | None = None
    notes: str | None = None
    tracking_number: str | None = None


class OrderAccept(BaseModel):
    """Order Staff acceptance payload."""
    notes: str | None = None


class OrderShip(BaseModel):
    """Shipping payload with optional tracking."""
    tracking_number: str | None = None
    carrier: str | None = None
    shipped_at: datetime | None = None


class OrderClose(BaseModel):
    """Closure payload."""
    notes: str | None = None


class Order(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    customer_id: uuid.UUID
    status: OrderStatus
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    invoice_id: uuid.UUID | None
    tracking_number: str | None
    created_at: datetime
    updated_at: datetime


class OrderListItem(BaseModel):
    """Lightweight order summary for list views."""
    id: uuid.UUID
    code: str
    status: OrderStatus
    total_amount: Decimal
    currency: str
    created_at: datetime
    customer_name: str | None


class LineItemWithProduct(LineItem):
    """Line item enriched with product name/sku for display."""
    product_name: str | None = None
    product_sku: str | None = None


class OrderWithItems(Order):
    """Full order with line items and customer name."""
    items: list[LineItem] = []
    customer_name: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Invoice
# ─────────────────────────────────────────────────────────────────────────────

class InvoiceBase(BaseModel):
    order_id: uuid.UUID
    issue_date: date | None = None
    due_date: date | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceIssue(BaseModel):
    due_date: date = Field(ge=date.today())


class InvoicePay(BaseModel):
    payment_method: str | None = None


class Invoice(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    order_id: uuid.UUID
    customer_id: uuid.UUID
    status: InvoiceStatus
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    paid_date: date | None
    billing_name: str | None
    billing_address: str | None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Payment
# ─────────────────────────────────────────────────────────────────────────────

class PaymentBase(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=4)
    currency: str = Field(default="USD", max_length=3)
    method: str | None = None
    gateway: str | None = None
    gateway_txn_id: str | None = None


class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime


class PaymentWebhookPayload(BaseModel):
    """Incoming webhook payload from payment gateway."""
    reference: str = Field(min_length=1, max_length=128)
    status: PaymentStatus
    gateway_txn_id: str | None = Field(default=None, max_length=128)
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=4)
    currency: str | None = Field(default="USD", max_length=3)
    failure_reason: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log (output only)
# ─────────────────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor_id: uuid.UUID | None
    ip_address: str | None
    payload: dict[str, Any] | None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Pagination helper
# ─────────────────────────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


def paginate(items: list[Any], *, total: int, page: int, page_size: int) -> BaseModel:
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return BaseModel(
        model_config=ConfigDict(),
        **{
            "items": items,
            "pagination": PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                pages=pages,
            ).model_dump(),
        }
    )
