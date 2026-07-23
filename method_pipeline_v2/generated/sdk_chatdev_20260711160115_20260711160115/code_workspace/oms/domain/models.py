"""
Shared domain models (entities) used across the OMS.
All models use Pydantic for validation and SQLAlchemy mapping.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from oms.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole = UserRole.CUSTOMER
    order_history: list[str] = Field(default_factory=list)  # list of order IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    base_price: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = "USD"
    stock_available: int = 0
    last_modified: datetime = Field(default_factory=datetime.utcnow)


class LineItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = "USD"


class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    line_items: list[LineItem] = Field(default_factory=list)
    total_amount: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    currency: str = "USD"
    status: OrderStatus = OrderStatus.CREATED
    invoice_ref: Optional[str] = None
    version: int = 1  # optimistic-lock version
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    status: PaymentStatus = PaymentStatus.PENDING
    idempotency_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    customer_id: str
    billing_address: str
    total_amount: Decimal = Field(max_digits=14, decimal_places=2)
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
