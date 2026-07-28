"""Pydantic schemas with strict validation matching Field Constraint Table"""
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator

# Helper regex patterns
NAME_REGEX = re.compile(r"^[\p{L} .'-]+$", re.UNICODE)
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")
ACCOUNT_REGEX = re.compile(r"^\d{6,20}$")
BANKNAME_REGEX = re.compile(r"^[\p{L}0-9 .&-]+$", re.UNICODE)
CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")
DATE_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")

class BankingDetails(BaseModel):
    accountNumber: str = Field(..., min_length=6, max_length=20)
    bankName: str = Field(..., min_length=2, max_length=100)

    @validator('accountNumber')
    def account_number_format(cls, v):
        if not ACCOUNT_REGEX.fullmatch(v):
            raise ValueError('accountNumber must be numeric 6-20 digits')
        return v

    @validator('bankName')
    def bank_name_format(cls, v):
        if not BANKNAME_REGEX.fullmatch(v):
            raise ValueError('bankName contains invalid characters')
        return v

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15)
    bankingDetails: BankingDetails
    role: str = Field(...)

    @validator('name')
    def name_format(cls, v):
        if not NAME_REGEX.fullmatch(v):
            raise ValueError('Invalid name format')
        return v.strip()

    @validator('address')
    def address_not_blank(cls, v):
        if not v.strip():
            raise ValueError('address cannot be blank')
        return v

    @validator('phone')
    def phone_format(cls, v):
        if not PHONE_REGEX.fullmatch(v):
            raise ValueError('Invalid phone format')
        return v

    @validator('role')
    def role_allowed(cls, v):
        if v not in {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}:
            raise ValueError('Invalid role')
        return v

class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    bankingDetails: BankingDetails
    role: str
    created_at: datetime

    class Config:
        orm_mode = True

class ProductCreate(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    price_amount: Decimal = Field(..., gt=Decimal('0.00'), lt=Decimal('1000000'))
    price_currency: str = Field(..., min_length=3, max_length=3)

    @validator('price_amount')
    def two_decimal_places(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('price_amount must have exactly 2 decimal places')
        return v

    @validator('price_currency')
    def currency_allowed(cls, v):
        if not CURRENCY_REGEX.fullmatch(v):
            raise ValueError('Invalid currency format')
        if v not in {"USD", "VND", "EUR"}:
            raise ValueError('Unsupported currency')
        return v

class ProductResponse(BaseModel):
    id: str
    description: str
    price_amount: Decimal
    price_currency: str
    created_at: datetime

    class Config:
        orm_mode = True

class LineItem(BaseModel):
    productRef: str = Field(..., min_length=36, max_length=36)
    quantity: int = Field(..., ge=1, le=1000)

    @validator('productRef')
    def uuid_format(cls, v):
        try:
            uuid.UUID(v, version=4)
        except Exception:
            raise ValueError('productRef must be a valid UUIDv4')
        return v

class OrderCreate(BaseModel):
    customerRef: str = Field(..., min_length=36, max_length=36)
    lineItems: List[LineItem] = Field(..., min_items=1, max_items=100)

    @validator('customerRef')
    def uuid_format(cls, v):
        try:
            uuid.UUID(v, version=4)
        except Exception:
            raise ValueError('customerRef must be a valid UUIDv4')
        return v

    @root_validator
    def no_duplicate_products(cls, values):
        items = values.get('lineItems') or []
        refs = [i.productRef for i in items]
        if len(set(refs)) != len(refs):
            raise ValueError('Duplicate productRef in line items')
        return values

class OrderResponse(BaseModel):
    id: str
    customerRef: str
    lineItems: List[LineItem]
    totalAmount: Decimal
    status: str
    createdAt: datetime
    updatedAt: datetime
    invoiceRef: Optional[str] = None

    class Config:
        orm_mode = True

# Invoice Schemas
class InvoiceCreate(BaseModel):
    orderRef: str = Field(..., min_length=36, max_length=36)
    billingInfo_name: str = Field(..., min_length=2, max_length=100)
    billingInfo_address: str = Field(..., min_length=5, max_length=255)
    issueDate: str = Field(..., min_length=10, max_length=10)
    dueDate: Optional[str] = None
    totalAmount: Decimal = Field(..., gt=Decimal('0.00'), lt=Decimal('100000000'))

    @validator('orderRef')
    def uuid_format(cls, v):
        try:
            uuid.UUID(v, version=4)
        except Exception:
            raise ValueError('orderRef must be a valid UUIDv4')
        return v

    @validator('billingInfo_name')
    def name_format(cls, v):
        if not NAME_REGEX.fullmatch(v):
            raise ValueError('Invalid name format')
        return v.strip()

    @validator('billingInfo_address')
    def address_not_blank(cls, v):
        if not v.strip():
            raise ValueError('address cannot be blank')
        return v

    @validator('issueDate')
    def issue_date_valid(cls, v):
        if not DATE_REGEX.fullmatch(v):
            raise ValueError('Invalid issueDate format')
        day, month, year = map(int, v.split('/') )
        try:
            datetime(year, month, day)
        except ValueError:
            raise ValueError('issueDate is not a real calendar date')
        return v

    @validator('dueDate', always=True)
    def due_date_valid(cls, v, values):
        issue = values.get('issueDate')
        if v is None:
            # default will be computed in service (issue + 7 days)
            return v
        if not DATE_REGEX.fullmatch(v):
            raise ValueError('Invalid dueDate format')
        day, month, year = map(int, v.split('/') )
        try:
            due = datetime(year, month, day)
        except ValueError:
            raise ValueError('dueDate is not a real calendar date')
        if issue:
            i_day, i_month, i_year = map(int, issue.split('/') )
            issue_dt = datetime(i_year, i_month, i_day)
            if due < issue_dt:
                raise ValueError('dueDate cannot precede issueDate')
        return v

class InvoiceResponse(BaseModel):
    id: str
    orderRef: str
    billingInfo: Dict[str, Any]
    totalAmount: Decimal
    issueDate: str
    dueDate: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# Payment Schemas
class PaymentCreate(BaseModel):
    orderRef: str = Field(..., min_length=36, max_length=36)
    amount: Decimal = Field(..., gt=Decimal('0.00'), lt=Decimal('100000000'))
    method: str = Field(...)

    @validator('orderRef')
    def uuid_format(cls, v):
        try:
            uuid.UUID(v, version=4)
        except Exception:
            raise ValueError('orderRef must be a valid UUIDv4')
        return v

    @validator('method')
    def method_allowed(cls, v):
        if v not in {"CREDIT_CARD", "BANK_TRANSFER", "E_WALLET"}:
            raise ValueError('Invalid payment method')
        return v

    @validator('amount')
    def two_decimal_places(cls, v):
        if v.quantize(Decimal('0.01')) != v:
            raise ValueError('amount must have exactly 2 decimal places')
        return v

class PaymentResponse(BaseModel):
    id: str
    orderRef: str
    amount: Decimal
    timestamp: datetime
    status: str
    method: str

    class Config:
        orm_mode = True
