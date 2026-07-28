import regex as re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator, model_validator, ValidationError

# Regex patterns using the `regex` library which supports Unicode properties
NAME_REGEX = re.compile(r"^[\p{L} .'-]+$", re.UNICODE)
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")
ACCOUNT_NUMBER_REGEX = re.compile(r"^\d{6,20}$")
BANK_NAME_REGEX = re.compile(r"^[\p{L}0-9 .\&-]+$", re.UNICODE)
CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")
PRICE_REGEX = re.compile(r"^\d{1,6}\.\d{2}$")
DATE_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4}$")

class BankingDetails(BaseModel):
    accountNumber: str = Field(..., min_length=6, max_length=20, pattern=ACCOUNT_NUMBER_REGEX.pattern)
    bankName: str = Field(..., min_length=2, max_length=100, pattern=BANK_NAME_REGEX.pattern)

class CustomerCreateDTO(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, pattern=NAME_REGEX.pattern)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15, pattern=PHONE_REGEX.pattern)
    bankingDetails: BankingDetails
    role: str = Field(...)

    @validator('role')
    def role_allowed(cls, v):
        if v not in {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}:
            raise ValueError('Invalid role')
        return v

    @validator('name')
    def name_not_blank(cls, v):
        if not v.strip():
            raise ValueError('name cannot be blank')
        return v

    @validator('address')
    def address_not_blank(cls, v):
        if not v.strip():
            raise ValueError('address cannot be blank')
        return v

class LineItemDTO(BaseModel):
    productRef: UUID = Field(..., description="Product UUID")
    quantity: int = Field(..., ge=1, le=1000)

class OrderCreateDTO(BaseModel):
    customerRef: UUID = Field(..., description="Customer UUID")
    lineItems: List[LineItemDTO] = Field(..., min_items=1, max_items=100)

    @validator('lineItems')
    def no_duplicate_products(cls, v):
        refs = [item.productRef for item in v]
        if len(set(refs)) != len(refs):
            raise ValueError('Duplicate productRef in line items')
        return v

class ProductCreateDTO(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    price_amount: Decimal = Field(...)
    price_currency: str = Field(..., min_length=3, max_length=3, pattern=CURRENCY_REGEX.pattern)

    @validator('price_amount')
    def amount_constraints(cls, v: Decimal):
        if v < Decimal('0.01') or v > Decimal('999999.99'):
            raise ValueError('price amount out of bounds')
        # enforce exactly two decimal places
        if v.as_tuple().exponent != -2:
            raise ValueError('price must have exactly 2 decimal places')
        return v

    @validator('price_currency')
    def currency_supported(cls, v):
        if v not in {"USD", "VND", "EUR"}:
            raise ValueError('Unsupported currency')
        return v

class CheckoutSummaryDTO(BaseModel):
    orderId: UUID
    totalAmount: str
    lineItems: List[dict]

class InvoiceCreateDTO(BaseModel):
    orderRef: UUID
    billingInfo_name: str = Field(..., min_length=2, max_length=100, alias='billingInfo.name')
    billingInfo_address: str = Field(..., min_length=5, max_length=255, alias='billingInfo.address')
    issueDate: Optional[str] = None
    dueDate: Optional[str] = None

    @model_validator(mode='before')
    def validate_dates_format(cls, values):
        # Validate format
        for field_name in ('issueDate', 'dueDate'):
            v = values.get(field_name)
            if v is None:
                continue
            if not DATE_REGEX.fullmatch(v):
                raise ValueError(f"{field_name} does not match dd/MM/yyyy")
        # Calendar validation and logical order
        def to_date(s: str) -> datetime:
            day, month, year = map(int, s.split('/'))
            return datetime(year, month, day)  # will raise ValueError for invalid date
        issue = values.get('issueDate')
        due = values.get('dueDate')
        if issue:
            to_date(issue)  # raises if invalid
        if due:
            due_dt = to_date(due)
            if issue:
                issue_dt = to_date(issue)
                if due_dt < issue_dt:
                    raise ValueError('dueDate must be >= issueDate')
        return values

class PaymentCreateDTO(BaseModel):
    orderRef: UUID
    amount: Decimal = Field(...)
    method: str = Field(...)

    @validator('amount')
    def amount_constraints(cls, v: Decimal):
        if v < Decimal('0.01') or v > Decimal('99999999.99'):
            raise ValueError('amount out of bounds')
        if v.as_tuple().exponent != -2:
            raise ValueError('amount must have exactly 2 decimal places')
        return v

    @validator('method')
    def method_allowed(cls, v):
        if v not in {"CREDIT_CARD", "BANK_TRANSFER", "E_WALLET"}:
            raise ValueError('Invalid payment method')
        return v

class PaymentVerifyDTO(BaseModel):
    paymentId: UUID
    status: str = Field(...)

    @validator('status')
    def status_allowed(cls, v):
        if v not in {"VERIFIED", "REJECTED"}:
            raise ValueError('Invalid payment verification status')
        return v
