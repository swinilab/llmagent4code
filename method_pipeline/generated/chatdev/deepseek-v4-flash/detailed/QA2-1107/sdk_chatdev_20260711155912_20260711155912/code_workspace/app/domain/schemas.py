"""
Pydantic schemas for API request/response serialisation and validation.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import (
    Currency,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


# ── Customer ───────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: UserRole = UserRole.CUSTOMER


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


# ── Product ────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    description: str = Field(..., min_length=1)
    base_price: float = Field(..., gt=0)
    currency: Currency = Currency.USD
    available: bool = True


class ProductResponse(BaseModel):
    id: uuid.UUID
    description: str
    base_price: float
    currency: Currency
    available: bool
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


# ── Order Line Item ────────────────────────────────────────────────────────

class OrderLineItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., gt=0)
    currency: Currency = Currency.USD


class OrderLineItemResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: float
    currency: Currency

    model_config = {"from_attributes": True}


# ── Order ──────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    line_items: list[OrderLineItemCreate] = Field(..., min_length=1)
    currency: Currency = Currency.USD


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    status: OrderStatus
    total_amount: float
    currency: Currency
    invoice_ref: str | None = None
    created_at: datetime
    updated_at: datetime
    version: int
    accepted_at_ts: datetime | None = None
    invoiced_at_ts: datetime | None = None
    paid_at_ts: datetime | None = None
    shipped_at_ts: datetime | None = None
    closed_at_ts: datetime | None = None
    cancelled_at_ts: datetime | None = None
    line_items: list[OrderLineItemResponse] = []

    model_config = {"from_attributes": True}


class OrderTransitionRequest(BaseModel):
    """Request body for order state transitions."""
    event: str = Field(..., description="Transition event name")
    # Optional payload for specific transitions
    invoice_ref: str | None = None
    payment_id: str | None = None


# ── Payment ───────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    order_id: uuid.UUID
    amount: float = Field(..., gt=0)
    method: PaymentMethod
    idempotency_key: str = Field(..., min_length=1)


class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    payment_timestamp: datetime
    status: PaymentStatus
    method: PaymentMethod
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


# ── Invoice ───────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    order_id: uuid.UUID
    billing_info: str = Field(..., min_length=1)
    amount: float | None = Field(
        default=None,
        description="Invoice amount. If omitted, defaults to the order's total_amount.",
    )
    currency: Currency = Currency.USD
    due_date: datetime


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    billing_info: str
    amount: float
    currency: Currency
    issue_date: datetime
    due_date: datetime
    status: InvoiceStatus
    created_at: datetime
    updated_at: datetime
    version: int

    model_config = {"from_attributes": True}


# ── Health ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: str
    uptime_seconds: float | None = None
