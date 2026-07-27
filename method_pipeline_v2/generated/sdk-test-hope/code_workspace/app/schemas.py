from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
import regex as re
import datetime
import uuid
from decimal import Decimal, InvalidOperation

# Helper validators
uuid_regex = re.compile(r'^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[1-5][0-9a-fA-F]{3}\-[89abAB][0-9a-fA-F]{3}\-[0-9a-fA-F]{12}$')
name_regex = re.compile(r"^[\p{L} .'-]+$", re.UNICODE)
phone_regex = re.compile(r'^\+?[1-9]\d{7,14}$')
account_regex = re.compile(r'^\d{6,20}$')
bank_name_regex = re.compile(r'^[\p{L}0-9 .&-]+$')
currency_regex = re.compile(r'^[A-Z]{3}$')
price_regex = re.compile(r'^\d{1,6}\.\d{2}$')
date_regex = re.compile(r'^\d{2}/\d{2}/\d{4}$')

SUPPORTED_CURRENCIES = {"USD", "VND", "EUR"}

class BankingDetails(BaseModel):
    accountNumber: str = Field(..., min_length=6, max_length=20)
    bankName: str = Field(..., min_length=2, max_length=100)

    @field_validator('accountNumber')
    @classmethod
    def account_number_format(cls, v: str) -> str:
        if not account_regex.fullmatch(v):
            raise ValueError('accountNumber must be numeric 6-20 digits')
        return v

    @field_validator('bankName')
    @classmethod
    def bank_name_format(cls, v: str) -> str:
        if not bank_name_regex.fullmatch(v):
            raise ValueError('bankName contains invalid characters')
        return v

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15)
    bankingDetails: BankingDetails
    role: str = Field(...)

    @field_validator('name')
    @classmethod
    def name_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('name cannot be blank')
        if not name_regex.fullmatch(v):
            raise ValueError('Invalid name format')
        return v.strip()

    @field_validator('address')
    @classmethod
    def address_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('address cannot be blank')
        return v

    @field_validator('phone')
    @classmethod
    def phone_valid(cls, v: str) -> str:
        if not phone_regex.fullmatch(v):
            raise ValueError('Invalid phone format')
        return v

    @field_validator('role')
    @classmethod
    def role_allowed(cls, v: str) -> str:
        if v not in {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}:
            raise ValueError('Invalid role')
        return v

    @model_validator(mode='after')
    def generate_id(self):
        # id is generated server-side; not part of input
        return self

class ProductCreate(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    price: dict

    @field_validator('description')
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('description cannot be blank')
        return v

    @field_validator('price')
    @classmethod
    def price_structure(cls, v: dict) -> dict:
        if 'amount' not in v or 'currency' not in v:
            raise ValueError('price must contain amount and currency')
        try:
            amount = Decimal(str(v['amount']))
        except (InvalidOperation, TypeError):
            raise ValueError('price.amount must be a valid decimal')
        
        if amount.as_tuple().exponent != -2:
            raise ValueError('price.amount must have exactly 2 decimal places')
        if not (Decimal('0.01') <= amount <= Decimal('999999.99')):
            raise ValueError('price.amount out of allowed range')
        
        currency = v['currency']
        if not currency_regex.fullmatch(currency) or currency not in SUPPORTED_CURRENCIES:
            raise ValueError('Unsupported currency')
        
        v['amount'] = amount
        return v

class LineItemCreate(BaseModel):
    productRef: str
    quantity: int = Field(..., ge=1, le=1000)

    @field_validator('productRef')
    @classmethod
    def uuid_valid(cls, v: str) -> str:
        if not uuid_regex.fullmatch(v):
            raise ValueError('Invalid UUID for productRef')
        return v

    @field_validator('quantity')
    @classmethod
    def quantity_range(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError('quantity out of bounds')
        return v

class OrderCreate(BaseModel):
    customerRef: str
    lineItems: List[LineItemCreate]

    @field_validator('customerRef')
    @classmethod
    def uuid_valid(cls, v: str) -> str:
        if not uuid_regex.fullmatch(v):
            raise ValueError('Invalid UUID for customerRef')
        return v

    @field_validator('lineItems')
    @classmethod
    def items_constraints(cls, v: List[LineItemCreate]) -> List[LineItemCreate]:
        if not (1 <= len(v) <= 100):
            raise ValueError('lineItems must contain 1-100 items')
        refs = [item.productRef for item in v]
        if len(set(refs)) != len(refs):
            raise ValueError('Duplicate productRef in lineItems')
        return v

class PaymentCreate(BaseModel):
    orderRef: str
    amount: Decimal
    method: str

    @field_validator('orderRef')
    @classmethod
    def uuid_valid(cls, v: str) -> str:
        if not uuid_regex.fullmatch(v):
            raise ValueError('Invalid UUID for orderRef')
        return v

    @field_validator('amount')
    @classmethod
    def amount_format(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent != -2:
            raise ValueError('amount must have exactly 2 decimal places')
        if not (Decimal('0.01') <= v <= Decimal('99999999.99')):
            raise ValueError('amount out of allowed range')
        return v

    @field_validator('method')
    @classmethod
    def method_allowed(cls, v: str) -> str:
        if v not in {"CREDIT_CARD", "BANK_TRANSFER", "E_WALLET"}:
            raise ValueError('Invalid payment method')
        return v

class InvoiceCreate(BaseModel):
    orderRef: str
    issueDate: str
    dueDate: Optional[str] = None

    @field_validator('orderRef')
    @classmethod
    def uuid_valid(cls, v: str) -> str:
        if not uuid_regex.fullmatch(v):
            raise ValueError('Invalid UUID for orderRef')
        return v

    @field_validator('issueDate')
    @classmethod
    def issue_date_format(cls, v: str) -> str:
        if not date_regex.fullmatch(v):
            raise ValueError('Invalid issueDate format')
        day, month, year = map(int, v.split('/'))
        try:
            datetime.date(year, month, day)
        except ValueError:
            raise ValueError('issueDate is not a real calendar date')
        return v

    @model_validator(mode='after')
    def due_date_logic(self):
        if not self.issueDate:
            raise ValueError('issueDate required before dueDate')
        
        issue_day, issue_month, issue_year = map(int, self.issueDate.split('/'))
        issue_date = datetime.date(issue_year, issue_month, issue_day)
        
        if self.dueDate is None:
            self.dueDate = (issue_date + datetime.timedelta(days=7)).strftime('%d/%m/%Y')
            return self
        
        if not date_regex.fullmatch(self.dueDate):
            raise ValueError('Invalid dueDate format')
        
        day, month, year = map(int, self.dueDate.split('/'))
        try:
            due = datetime.date(year, month, day)
        except ValueError:
            raise ValueError('dueDate is not a real calendar date')
            
        if due < issue_date:
            raise ValueError('dueDate cannot be before issueDate')
            
        return self