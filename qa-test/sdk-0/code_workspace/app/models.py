from __future__ import annotations
import re
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator, root_validator

# Utility validators

def uuid4_str(value: str) -> str:
    try:
        u = uuid.UUID(value, version=4)
    except Exception:
        raise ValueError('Invalid UUIDv4 format')
    if str(u) != value:
        raise ValueError('UUID must be in canonical form')
    return value

# Enums
class Role(str):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"

class OrderStatus(str):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PaymentMethod(str):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"

class InvoiceStatus(str):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

# Shared sub-models
class BankingDetails(BaseModel):
    accountNumber: str = Field(..., min_length=6, max_length=20, regex=r"^\d{6,20}$")
    bankName: str = Field(..., min_length=2, max_length=100, regex=r"^[\p{L}0-9 .&-]+$")

    @validator('bankName')
    def validate_bank_name(cls, v):
        if not re.match(r"^[\p{L}0-9 .&-]+$", v, flags=re.UNICODE):
            raise ValueError('Invalid bank name format')
        return v

class Price(BaseModel):
    amount: Decimal = Field(..., gt=Decimal('0.00'), lt=Decimal('1000000.00'))
    currency: str = Field(..., min_length=3, max_length=3, regex=r"^[A-Z]{3}$")

    @validator('amount')
    def two_decimal_places(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('Amount must have exactly two decimal places')
        return v

class LineItem(BaseModel):
    productRef: str = Field(...)
    quantity: int = Field(..., ge=1, le=1000)
    unitPriceSnapshot: Decimal = Field(...)

    @validator('productRef')
    def validate_product_ref(cls, v):
        return uuid4_str(v)

    @validator('unitPriceSnapshot')
    def validate_price_snapshot(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('unitPriceSnapshot must have two decimal places')
        return v

# DTOs
class CustomerCreateDTO(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, regex=r"^[\p{L} .'-]+$")
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15, regex=r"^\+?[1-9]\d{7,14}$")
    bankingDetails: BankingDetails
    role: Role

    @validator('name')
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError('name cannot be blank')
        return v

    @validator('address')
    def not_blank_addr(cls, v):
        if not v.strip():
            raise ValueError('address cannot be blank')
        return v

class CustomerDTO(CustomerCreateDTO):
    id: str = Field(...)
    orderHistory: List[str] = Field(default_factory=list)

    @validator('id')
    def validate_id(cls, v):
        return uuid4_str(v)

class ProductCreateDTO(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    price: Price

    @validator('description')
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError('description cannot be blank')
        return v

class ProductDTO(ProductCreateDTO):
    id: str = Field(...)

    @validator('id')
    def validate_id(cls, v):
        return uuid4_str(v)

class OrderCreateDTO(BaseModel):
    customerRef: str = Field(...)
    lineItems: List[LineItem] = Field(..., min_items=1, max_items=100)

    @validator('customerRef')
    def validate_customer_ref(cls, v):
        return uuid4_str(v)

    @root_validator
    def no_duplicate_products(cls, values):
        items = values.get('lineItems') or []
        refs = [i.productRef for i in items]
        if len(set(refs)) != len(refs):
            raise ValueError('Duplicate productRef in line items')
        return values

class OrderDTO(OrderCreateDTO):
    id: str = Field(...)
    totalAmount: Decimal = Field(...)
    status: OrderStatus = Field(default=OrderStatus.PLACED)
    createdAt: datetime = Field(...)
    updatedAt: datetime = Field(...)
    invoiceRef: Optional[str] = None

    @validator('id')
    def validate_id(cls, v):
        return uuid4_str(v)

    @validator('invoiceRef')
    def validate_invoice_ref(cls, v):
        if v is not None:
            return uuid4_str(v)
        return v

class PaymentCreateDTO(BaseModel):
    orderRef: str = Field(...)
    amount: Decimal = Field(..., gt=Decimal('0.00'))
    method: PaymentMethod = Field(...)

    @validator('orderRef')
    def validate_order_ref(cls, v):
        return uuid4_str(v)

    @validator('amount')
    def validate_amount(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('Amount must have two decimal places')
        return v

class PaymentDTO(PaymentCreateDTO):
    id: str = Field(...)
    timestamp: datetime = Field(...)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    @validator('id')
    def validate_id(cls, v):
        return uuid4_str(v)

class InvoiceCreateDTO(BaseModel):
    orderRef: str = Field(...)
    billingInfo_name: str = Field(..., min_length=2, max_length=100, alias='billingInfo.name', regex=r"^[\p{L} .'-]+$")
    billingInfo_address: str = Field(..., min_length=5, max_length=255, alias='billingInfo.address')
    totalAmount: Decimal = Field(...)
    issueDate: str = Field(..., regex=r"^\d{2}/\d{2}/\d{4}$")
    dueDate: Optional[str] = Field(None, regex=r"^\d{2}/\d{2}/\d{4}$")

    @validator('orderRef')
    def validate_order_ref(cls, v):
        return uuid4_str(v)

    @validator('totalAmount')
    def validate_total_amount(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('totalAmount must have two decimal places')
        return v

    @validator('issueDate')
    def validate_issue_date(cls, v):
        day, month, year = map(int, v.split('/'))
        try:
            date(year, month, day)
        except ValueError:
            raise ValueError('Invalid issueDate')
        return v

    @validator('dueDate', always=True)
    def validate_due_date(cls, v, values):
        issue = values.get('issueDate')
        day_i, month_i, year_i = map(int, issue.split('/'))
        issue_dt = date(year_i, month_i, day_i)
        if v is None:
            return (issue_dt + timedelta(days=7)).strftime('%d/%m/%Y')
        day, month, year = map(int, v.split('/'))
        try:
            due_dt = date(year, month, day)
        except ValueError:
            raise ValueError('Invalid dueDate')
        if due_dt < issue_dt:
            raise ValueError('dueDate cannot be before issueDate')
        return v

class InvoiceDTO(InvoiceCreateDTO):
    id: str = Field(...)
    status: InvoiceStatus = Field(default=InvoiceStatus.ISSUED)

    @validator('id')
    def validate_id(cls, v):
        return uuid4_str(v)
