"""
Pydantic schemas for API request/response serialisation.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import (
    CustomerRole,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: CustomerRole = CustomerRole.CUSTOMER


class CustomerResponse(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    banking_details: str
    role: CustomerRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductCreate(BaseModel):
    description: str = Field(..., min_length=1)
    base_price: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", max_length=3)
    stock_available: int = Field(default=0, ge=0)


class ProductResponse(BaseModel):
    id: int
    description: str
    base_price: Decimal
    currency: str
    stock_available: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductSearchParams(BaseModel):
    q: Optional[str] = Field(default=None, description="Full-text search query")
    min_price: Optional[Decimal] = Field(default=None, ge=0)
    max_price: Optional[Decimal] = Field(default=None, ge=0)
    in_stock_only: bool = False
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderLineItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    customer_id: int = Field(..., gt=0)
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1)


class OrderLineItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    currency: str

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: OrderStatus
    total_amount: Decimal
    currency: str
    version: int
    created_at: datetime
    updated_at: datetime
    line_items: List[OrderLineItemResponse] = []

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    new_status: OrderStatus
    version: int = Field(..., ge=1, description="Optimistic-lock version")


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", max_length=3)
    method: PaymentMethod
    version: int = Field(..., ge=1, description="Optimistic-lock version of the order")


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentVerification(BaseModel):
    payment_id: int = Field(..., gt=0)
    status: PaymentStatus
    order_version: int = Field(..., ge=1, description="Optimistic-lock version of the order")


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

class InvoiceCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    billing_name: str = Field(..., min_length=1)
    billing_address: str = Field(..., min_length=1)
    due_date: Optional[date] = None
    version: int = Field(..., ge=1, description="Optimistic-lock version of the order")


class InvoiceResponse(BaseModel):
    id: int
    order_id: int
    billing_name: str
    billing_address: str
    total_amount: Decimal
    currency: str
    status: InvoiceStatus
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    error_code: str = "UNKNOWN"


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
