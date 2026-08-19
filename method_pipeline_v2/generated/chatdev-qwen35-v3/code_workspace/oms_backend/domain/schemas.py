"""
Pydantic schemas for request/response validation
Implements all field constraints from the Field Constraint Table
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import re
import uuid


class CustomerRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class InvoiceStatus(str, Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


def validate_uuid4(value: str) -> str:
    """Validate UUIDv4 format"""
    try:
        uuid.UUID(value, version=4)
        return value
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid UUID format: {value}")


def validate_phone(value: str) -> str:
    """Validate phone: E.164, 8-15 digits after optional +"""
    if not re.match(r'^\+?[1-9]\d{7,14}$', value):
        raise ValueError("Phone must be E.164 format (8-15 digits)")
    return value


def validate_name(value: str) -> str:
    """Validate name: 2-100 chars, letters/spaces/dots/hyphens/apostrophes"""
    if not value or len(value) < 2 or len(value) > 100:
        raise ValueError("Name must be 2-100 characters")
    if not re.match(r'^[\w .\'-]+$', value, re.UNICODE):
        raise ValueError("Name contains invalid characters")
    if value.strip() == "":
        raise ValueError("Name cannot be blank")
    return value


def validate_address(value: str) -> str:
    """Validate address: 5-255 chars, not blank"""
    if not value or len(value) < 5 or len(value) > 255:
        raise ValueError("Address must be 5-255 characters")
    if value.strip() == "":
        raise ValueError("Address cannot be blank")
    return value


def validate_account_number(value: str) -> str:
    """Validate account number: 6-20 digits"""
    if not value or len(value) < 6 or len(value) > 20:
        raise ValueError("Account number must be 6-20 digits")
    if not value.isdigit():
        raise ValueError("Account number must be numeric only")
    return value


def validate_bank_name(value: str) -> str:
    """Validate bank name: 2-100 chars"""
    if not value or len(value) < 2 or len(value) > 100:
        raise ValueError("Bank name must be 2-100 characters")
    return value


def validate_description(value: str) -> str:
    """Validate description: 3-500 chars, not blank"""
    if not value or len(value) < 3 or len(value) > 500:
        raise ValueError("Description must be 3-500 characters")
    if value.strip() == "":
        raise ValueError("Description cannot be blank")
    return value


def validate_currency(value: str) -> str:
    """Validate currency: 3 uppercase letters, must be USD/VND/EUR"""
    if not value or len(value) != 3:
        raise ValueError("Currency must be 3 characters")
    if not re.match(r'^[A-Z]{3}$', value):
        raise ValueError("Currency must be uppercase letters")
    if value not in ["USD", "VND", "EUR"]:
        raise ValueError("Currency must be USD, VND, or EUR")
    return value


def validate_price_amount(value: float) -> float:
    """Validate price: 0.01 to 999999.99, exactly 2 decimal places"""
    # Check decimal places
    str_val = str(value)
    if '.' in str_val:
        decimal_part = str_val.split('.')[1]
        if len(decimal_part) != 2:
            raise ValueError("Price must have exactly 2 decimal places")
    if not (0.01 <= value <= 999999.99):
        raise ValueError("Price must be between 0.01 and 999999.99")
    return value


def validate_date_ddmmyyyy(value: str) -> str:
    """Validate date: dd/MM/yyyy format with calendar check"""
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', value):
        raise ValueError("Date must be dd/MM/yyyy format")
    try:
        day, month, year = map(int, value.split('/'))
        datetime(year=year, month=month, day=day)
    except ValueError:
        raise ValueError(f"Invalid calendar date: {value}")
    return value


class BankingDetails(BaseModel):
    """Banking details nested object"""
    accountNumber: str = Field(..., min_length=6, max_length=20)
    bankName: str = Field(..., min_length=2, max_length=100)
    
    _validate_account = field_validator('accountNumber')(validate_account_number)
    _validate_bank = field_validator('bankName')(validate_bank_name)


class Price(BaseModel):
    """Price nested object"""
    amount: float
    currency: str
    
    _validate_amount = field_validator('amount')(validate_price_amount)
    _validate_currency = field_validator('currency')(validate_currency)

class LineItem(BaseModel):
    """Order line item (input schema - unitPriceSnapshot is server-computed)"""
    productRef: str
    quantity: int = Field(..., ge=1, le=1000)
    unitPriceSnapshot: Optional[float] = None  # Optional for input, server-computed
    
    _validate_product_ref = field_validator('productRef')(validate_uuid4)
    _validate_unit_price = field_validator('unitPriceSnapshot')(validate_price_amount)


class LineItemResponse(BaseModel):
    """Order line item response (includes server-computed unitPriceSnapshot)"""
    productRef: str
    quantity: int
    unitPriceSnapshot: float  # Required in response
    
    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    """Customer creation schema"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str
    bankingDetails: BankingDetails
    role: CustomerRole = CustomerRole.CUSTOMER
    
    _validate_name = field_validator('name')(validate_name)
    _validate_address = field_validator('address')(validate_address)
    _validate_phone = field_validator('phone')(validate_phone)


class CustomerResponse(BaseModel):
    """Customer response schema"""
    id: str
    name: str
    address: str
    phone: str
    bankingDetails: BankingDetails
    role: CustomerRole
    orderHistory: List[str]
    createdAt: datetime
    updatedAt: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Product creation schema"""
    description: str = Field(..., min_length=3, max_length=500)
    price: Price
    
    _validate_description = field_validator('description')(validate_description)


class ProductResponse(BaseModel):
    """Product response schema"""
    id: str
    description: str
    price: Price
    createdAt: datetime
    updatedAt: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    """Order response schema"""
    id: str
    customerRef: str
    lineItems: List[LineItemResponse]  # Use response schema with unitPriceSnapshot
    totalAmount: float
    status: OrderStatus
    invoiceRef: Optional[str]
    createdAt: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Order creation schema (client provides customerRef and lineItems only)"""
    customerRef: str
    lineItems: List[LineItem]
    
    _validate_customer_ref = field_validator('customerRef')(validate_uuid4)

class PaymentCreate(BaseModel):
    """Payment creation schema"""
    orderRef: str
    amount: float
    method: PaymentMethod
    
    _validate_order_ref = field_validator('orderRef')(validate_uuid4)
    _validate_amount = field_validator('amount')(validate_price_amount)


class PaymentResponse(BaseModel):
    """Payment response schema"""
    id: str
    orderRef: str
    amount: float
    timestamp: datetime
    status: PaymentStatus
    method: PaymentMethod
    
    model_config = ConfigDict(from_attributes=True)


class BillingInfo(BaseModel):
    """Billing info nested object"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    
    _validate_name = field_validator('name')(validate_name)
    _validate_address = field_validator('address')(validate_address)


class InvoiceCreate(BaseModel):
    """Invoice creation schema"""
    orderRef: str
    billingInfo: BillingInfo
    totalAmount: float
    issueDate: str
    dueDate: str
    
    _validate_order_ref = field_validator('orderRef')(validate_uuid4)
    _validate_amount = field_validator('totalAmount')(validate_price_amount)
    _validate_issue_date = field_validator('issueDate')(validate_date_ddmmyyyy)
    _validate_due_date = field_validator('dueDate')(validate_date_ddmmyyyy)


class InvoiceResponse(BaseModel):
    """Invoice response schema"""
    id: str
    orderRef: str
    billingInfo: BillingInfo
    totalAmount: float
    issueDate: str
    dueDate: str
    status: InvoiceStatus
    
    model_config = ConfigDict(from_attributes=True)
