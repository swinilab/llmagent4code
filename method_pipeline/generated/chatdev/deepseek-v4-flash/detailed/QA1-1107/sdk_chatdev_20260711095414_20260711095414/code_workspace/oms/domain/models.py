"""
Shared domain models (Pydantic) used across the system.
"""
from __future__ import annotations

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, model_validator

from oms.domain.enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod, UserRole


def _utcnow() -> datetime:
    """Return timezone-aware UTC now for Pydantic default factories."""
    return datetime.now(timezone.utc)


# ── Customer ────────────────────────────────────────────────────────────────

class Customer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole = UserRole.CUSTOMER
    order_history: list[UUID] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_order_history(cls, data: dict) -> dict:
        """Convert order_history items from str (JSON column) to UUID."""
        if isinstance(data, dict):
            raw = data.get("order_history")
            if raw is not None and isinstance(raw, list):
                data["order_history"] = [
                    UUID(str(item)) if not isinstance(item, UUID) else item
                    for item in raw
                ]
        return data


# ── Product ──────────────────────────────────────────────────────────────────

class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    description: str
    base_price: Decimal = Field(..., decimal_places=2)
    currency: str = "USD"
    stock_available: int = 0
    last_modified: datetime = Field(default_factory=_utcnow)


# ── Order ────────────────────────────────────────────────────────────────────

class OrderLineItem(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., decimal_places=2)


class Order(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    line_items: list[OrderLineItem]
    subtotal: Decimal = Field(..., decimal_places=2)
    tax: Decimal = Field(..., decimal_places=2)
    total_amount: Decimal = Field(..., decimal_places=2)
    status: OrderStatus = OrderStatus.CREATED
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    accepted_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    invoice_ref: Optional[UUID] = None
    version: int = 1  # optimistic-lock


# ── Payment ──────────────────────────────────────────────────────────────────

class Payment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    amount: Decimal = Field(..., decimal_places=2)
    timestamp: datetime = Field(default_factory=_utcnow)
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod
    idempotency_key: str  # used for safe retries


# ── Invoice ──────────────────────────────────────────────────────────────────

class Invoice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    billing_info: str
    amount: Decimal = Field(..., decimal_places=2)
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    status: InvoiceStatus = InvoiceStatus.DRAFT
