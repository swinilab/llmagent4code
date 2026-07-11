"""
Pydantic schemas for API request/response validation and serialization.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------
class CustomerCreate(BaseModel):
    name: str = ""
    address: str = ""
    phone: str = ""
    banking_details: str = ""
    role: UserRole = UserRole.CUSTOMER


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
class ProductCreate(BaseModel):
    description: str = ""
    base_price: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: str = "USD"


class ProductResponse(BaseModel):
    id: UUID
    description: str
    base_price: Decimal
    currency: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Line Item
# ---------------------------------------------------------------------------
class LineItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: str = "USD"


class LineItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    currency: str
    total: Decimal

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
class OrderCreate(BaseModel):
    customer_id: UUID
    line_items: list[LineItemRequest] = Field(default_factory=list, min_length=1)


class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    invoice_id: Optional[UUID] = None
    payment_id: Optional[UUID] = None
    total_amount: Decimal = Decimal("0.00")
    line_items: list[LineItemResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class PaymentCreate(BaseModel):
    amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    timestamp: datetime

    class Config:
        from_attributes = True


class PaymentVerification(BaseModel):
    verified: bool = True


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class InvoiceCreate(BaseModel):
    billing_name: str = ""
    billing_address: str = ""
    due_days: int = Field(default=30, ge=1)


class InvoiceResponse(BaseModel):
    id: UUID
    order_id: UUID
    billing_name: str
    billing_address: str
    total_amount: Decimal
    currency: str
    issue_date: datetime
    due_date: datetime
    status: InvoiceStatus

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    database: str
    circuit_breakers: dict[str, str]
    version: str
