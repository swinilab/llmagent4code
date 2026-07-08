"""Domain shared models — used by both API schema and internal logic."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────
class OrderStatus(str, enum.Enum):
    """Full lifecycle of an order."""

    PENDING = "pending"  # Customer placed
    ACCEPTED = "accepted"  # Order staff reviewed & accepted
    INVOICED = "invoiced"  # Accountant created invoice
    PAID = "paid"  # Customer paid
    VERIFIED = "verified"  # Accountant verified payment
    SHIPPED = "shipped"  # Order staff shipped
    COMPLETED = "completed"  # Order staff closed


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


# ── Shared timestamp utility ──────────────────────────────────────────────────
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Pydantic domain models (shared between FE & BE) ───────────────────────────
class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    banking_details: str
    order_history: list[str] = Field(default_factory=list)
    role: UserRole = UserRole.CUSTOMER

    model_config = {"from_attributes": True}


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    base_price: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = "USD"

    model_config = {"from_attributes": True}


class LineItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(max_digits=12, decimal_places=2)
    subtotal: Decimal = Field(max_digits=12, decimal_places=2)

    model_config = {"from_attributes": True}


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    line_items: list[LineItem]
    total_amount: Decimal = Field(max_digits=12, decimal_places=2)
    status: OrderStatus = OrderStatus.PENDING
    invoice_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = {"from_attributes": True}


class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    invoice_id: str
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    timestamp: datetime = Field(default_factory=utcnow)

    model_config = {"from_attributes": True}


class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    customer_id: str
    billing_name: str
    billing_address: str
    total_amount: Decimal = Field(max_digits=12, decimal_places=2)
    issue_date: datetime = Field(default_factory=utcnow)
    due_date: datetime
    status: InvoiceStatus = InvoiceStatus.DRAFT

    model_config = {"from_attributes": True}