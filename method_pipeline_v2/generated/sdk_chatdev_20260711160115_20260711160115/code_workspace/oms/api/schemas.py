"""
Pydantic schemas for API request/response validation.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Customer ----------

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    banking_details: str = Field(..., min_length=1)
    role: str = "CUSTOMER"


class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: str
    created_at: datetime


# ---------- Product ----------

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""
    base_price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: str = "USD"
    stock_available: int = Field(default=0, ge=0)


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    base_price: str
    currency: str
    stock_available: int


# ---------- Order ----------

class LineItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class OrderCreate(BaseModel):
    customer_id: str
    line_items: list[LineItemRequest] = Field(..., min_length=1)


class LineItemResponse(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: str
    currency: str


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    line_items: list[LineItemResponse]
    total_amount: str
    currency: str
    status: str
    invoice_ref: Optional[str] = None
    version: int
    created_at: datetime
    accepted_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class OrderAction(BaseModel):
    version: int = Field(..., ge=1)


class InvoiceRequest(BaseModel):
    version: int = Field(..., ge=1)
    billing_address: str = Field(..., min_length=1)


class PaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    method: str = "CREDIT_CARD"
    idempotency_key: str = Field(..., min_length=1)


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    status: str
    idempotent: bool = False


class InvoiceResponse(BaseModel):
    invoice_id: str
    order_id: str
    total: str


class VerifyPaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    status: str
    amount: str
    completed_at: Optional[str] = None


# ---------- Generic ----------

class ErrorResponse(BaseModel):
    detail: str
