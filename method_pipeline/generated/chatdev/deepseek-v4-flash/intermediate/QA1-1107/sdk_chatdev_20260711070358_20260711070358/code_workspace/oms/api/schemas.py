"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    detail: str
    code: str = "ERROR"


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: str = Field(default="CUSTOMER", pattern=r"^(CUSTOMER|ORDER_STAFF|ACCOUNTANT)$")


class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    base_price: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    stock_available: bool = True


class ProductResponse(BaseModel):
    id: str
    description: str
    base_price: Decimal
    currency: str
    stock_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderLineItemRequest(BaseModel):
    product_id: str
    product_description: str = ""
    quantity: int = Field(..., ge=1, le=1000)
    unit_price: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")


class OrderCreate(BaseModel):
    customer_id: str
    line_items: List[OrderLineItemRequest] = Field(..., min_length=1)


class OrderLineItemResponse(BaseModel):
    product_id: str
    product_description: str
    quantity: int
    unit_price: Decimal
    currency: str

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    line_items: List[OrderLineItemResponse]
    status: str
    total_amount: Decimal
    currency: str
    invoice_ref: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransitionRequest(BaseModel):
    target_status: str = Field(..., pattern=r"^(ACCEPTED|INVOICED|PAID|SHIPPED|CLOSED|CANCELLED)$")
    expected_version: int = Field(..., ge=1)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0"))
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    method: str = Field(default="CREDIT_CARD", pattern=r"^(CREDIT_CARD|DEBIT_CARD|BANK_TRANSFER|DIGITAL_WALLET)$")


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    amount: Decimal
    currency: str
    method: str
    status: str
    timestamp: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    expected_version: int = Field(..., ge=1)
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None


class InvoiceResponse(BaseModel):
    id: str
    order_id: str
    billing_name: str
    billing_address: str
    total_amount: Decimal
    currency: str
    status: str
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentVerificationRequest(BaseModel):
    payment_id: str
    expected_version: int = Field(..., ge=1)
