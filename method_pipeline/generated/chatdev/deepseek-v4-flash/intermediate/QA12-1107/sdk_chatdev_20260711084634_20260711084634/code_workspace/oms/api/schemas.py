"""
Pydantic request/response schemas for the OMS API.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Customer schemas
# ---------------------------------------------------------------------------

class AddressSchema(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"


class BankingDetailsSchema(BaseModel):
    account_holder: str
    account_number: str
    routing_number: str
    bank_name: str


class CustomerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = ""
    address: Optional[AddressSchema] = None
    banking_details: Optional[BankingDetailsSchema] = None


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[AddressSchema] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: str
    address: Optional[dict] = None
    role: str
    created_at: datetime
    updated_at: datetime
    version: int


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------

class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    price_amount: Decimal = Field(..., gt=0)
    price_currency: str = "USD"
    stock: int = Field(0, ge=0)


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_amount: Optional[Decimal] = None
    price_currency: Optional[str] = None
    stock: Optional[int] = None
    available: Optional[bool] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    base_price_amount: str
    base_price_currency: str
    stock: int
    available: bool
    created_at: datetime
    updated_at: datetime
    version: int


# ---------------------------------------------------------------------------
# Order schemas
# ---------------------------------------------------------------------------

class LineItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class OrderCreateRequest(BaseModel):
    customer_id: str
    items: list[LineItemRequest] = Field(..., min_length=1)
    shipping_address: Optional[AddressSchema] = None
    notes: str = ""


class OrderPayRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    method: str = "CREDIT_CARD"


class LineItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price_amount: str
    unit_price_currency: str
    total_price_amount: str


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    line_items: list[dict]
    status: str
    total_amount: str
    total_currency: str
    invoice_ref: Optional[str] = None
    payment_ref: Optional[str] = None
    shipping_address: Optional[dict] = None
    notes: str
    created_at: datetime
    updated_at: datetime
    version: int


# ---------------------------------------------------------------------------
# Payment schemas
# ---------------------------------------------------------------------------

class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: str
    currency: str
    status: str
    method: str
    transaction_id: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    version: int


# ---------------------------------------------------------------------------
# Invoice schemas
# ---------------------------------------------------------------------------

class InvoiceResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    billing_address: Optional[dict] = None
    line_items: list[dict]
    subtotal: str
    tax: str
    total: str
    currency: str
    status: str
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    version: int


# ---------------------------------------------------------------------------
# Generic schemas
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    error_code: str = "UNKNOWN"


class HealthResponse(BaseModel):
    status: str
    checks: Optional[dict[str, str]] = None
    uptime_seconds: Optional[float] = None
