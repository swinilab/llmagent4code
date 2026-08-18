"""
Domain models for OMS - shared between frontend and backend
Implements all field constraints from the Field Constraint Table
"""
import re
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import phonenumbers

# ============== Enums ==============

class CustomerRole(str, Enum):
    """Customer role enumeration"""
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"

class OrderStatus(str, Enum):
    """Order status enumeration with full lifecycle"""
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"

class InvoiceStatus(str, Enum):
    """Invoice status enumeration"""
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

# ============== Validation Utilities ==============

def validate_uuid_format(value: str) -> str:
    """Validate UUIDv4 format"""
    try:
        uuid_obj = uuid.UUID(value, version=4)
        if str(uuid_obj) != value:
            raise ValueError("UUID format mismatch")
        return value
    except (ValueError, AttributeError):
        raise ValueError("Invalid UUIDv4 format")

def validate_name(value: str) -> str:
    """Validate name field: 2-100 chars, pattern ^[\\p{L} .'-]+$"""
    if not value or not value.strip():
        raise ValueError("Name must not be blank or whitespace-only")
    if len(value) < 2 or len(value) > 100:
        raise ValueError("Name must be 2-100 characters")
    # Unicode letter pattern
    # Unicode letter pattern: ^[\p{L} .'-]+$ (letters, spaces, dots, apostrophes, hyphens only - no digits or underscores)
    if not re.match(r'^[\p{L} .\'-]+$', value, re.UNICODE):
        raise ValueError("Name contains invalid characters")
    return value

def validate_address(value: str) -> str:
    """Validate address field: 5-255 chars, free text"""
    if not value or not value.strip():
        raise ValueError("Address must not be blank or whitespace-only")
    if len(value) < 5 or len(value) > 255:
        raise ValueError("Address must be 5-255 characters")
    return value

def validate_phone(value: str) -> str:
    """Validate phone field: E.164 format, 8-15 digits"""
    if not value:
        raise ValueError("Phone is required")
    # E.164 pattern: ^\+?[1-9]\d{7,14}$
    if not re.match(r'^\+?[1-9]\d{7,14}$', value):
        raise ValueError("Phone must be in E.164 format (8-15 digits)")
    return value

def validate_account_number(value: str) -> str:
    """Validate account number: 6-20 digits"""
    if not re.match(r'^\d{6,20}$', value):
        raise ValueError("Account number must be 6-20 digits")
    return value

def validate_bank_name(value: str) -> str:
    """Validate bank name: 2-100 chars, pattern ^[\\p{L}0-9 .&-]+$"""
    if not value or not value.strip():
        raise ValueError("Bank name must not be blank")
    if len(value) < 2 or len(value) > 100:
        raise ValueError("Bank name must be 2-100 characters")
    # Unicode letter pattern: ^[\p{L}0-9 .&-]+$ (letters, digits, spaces, dots, ampersands, hyphens only)
    if not re.match(r'^[\p{L}0-9 .&-]+$', value, re.UNICODE):
        raise ValueError("Bank name contains invalid characters")
    return value

def validate_product_description(value: str) -> str:
    """Validate product description: 3-500 chars"""
    if not value or not value.strip():
        raise ValueError("Description must not be blank")
    if len(value) < 3 or len(value) > 500:
        raise ValueError("Description must be 3-500 characters")
    return value

def validate_amount(value: Any, min_val: Decimal, max_val: Decimal, field_name: str) -> Decimal:
    """Validate decimal amount: exactly 2 decimal places, within range"""
    if isinstance(value, str):
        # Check exact 2 decimal places format
        if not re.match(r'^\d{1,6}\.\d{2}$', value):
            raise ValueError(f"{field_name} must have exactly 2 decimal places")
        try:
            value = Decimal(value)
        except InvalidOperation:
            raise ValueError(f"{field_name} is not a valid decimal")
    elif isinstance(value, (int, float)):
        value = Decimal(str(value))
    
    if value < min_val or value > max_val:
        raise ValueError(f"{field_name} must be between {min_val} and {max_val}")
    
    # Ensure exactly 2 decimal places
    value = value.quantize(Decimal('0.01'))
    return value

def validate_currency(value: str) -> str:
    """Validate currency: ISO 4217, 3 uppercase letters"""
    supported = {'USD', 'VND', 'EUR'}
    if not re.match(r'^[A-Z]{3}$', value):
        raise ValueError("Currency must be 3 uppercase letters")
    if value not in supported:
        raise ValueError(f"Currency must be one of {supported}")
    return value

def validate_date_ddmmyyyy(value: str, field_name: str = "Date") -> str:
    """Validate date in dd/MM/yyyy format with calendar semantics"""
    if not re.match(r'^\d{2}/\d{2}/\d{4}$', value):
        raise ValueError(f"{field_name} must be in dd/MM/yyyy format")
    try:
        day, month, year = map(int, value.split('/'))
        # Validate calendar semantics
        datetime(year=year, month=month, day=day)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} is not a valid calendar date")
    return value

def validate_quantity(value: int) -> int:
    """Validate quantity: 1-1000"""
    if not isinstance(value, int) or value < 1 or value > 1000:
        raise ValueError("Quantity must be an integer between 1 and 1000")
    return value

# ============== Domain Models ==============

class BankingDetails(BaseModel):
    """Banking details for customer"""
    accountNumber: str = Field(..., description="Account number 6-20 digits")
    bankName: str = Field(..., description="Bank name 2-100 characters")
    
    @field_validator('accountNumber')
    @classmethod
    def validate_account_number(cls, v):
        return validate_account_number(v)
    
    @field_validator('bankName')
    @classmethod
    def validate_bank_name(cls, v):
        return validate_bank_name(v)

class Price(BaseModel):
    """Product price with amount and currency"""
    amount: Decimal = Field(..., description="Price amount 0.01-999999.99")
    currency: str = Field(..., description="ISO 4217 currency code")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        return validate_amount(v, Decimal('0.01'), Decimal('999999.99'), 'Price amount')
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v):
        return validate_currency(v)

class LineItem(BaseModel):
    """Order line item"""
    productRef: str = Field(..., description="Product UUID reference")
    quantity: int = Field(..., description="Quantity 1-1000")
    unitPriceSnapshot: Optional[Decimal] = Field(None, description="Price snapshot (server-computed)")
    
    @field_validator('productRef')
    @classmethod
    def validate_product_ref(cls, v):
        return validate_uuid_format(v)
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        return validate_quantity(v)

class Customer(BaseModel):
    """Customer entity"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="UUIDv4, server-generated")
    name: str = Field(..., description="Customer name 2-100 chars")
    address: str = Field(..., description="Address 5-255 chars")
    phone: str = Field(..., description="E.164 phone number")
    bankingDetails: BankingDetails = Field(..., description="Banking details")
    role: CustomerRole = Field(..., description="Customer role")
    orderHistory: Optional[List[str]] = Field(None, description="Order history (read-only)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        return validate_address(v)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return validate_phone(v)

class CustomerCreate(BaseModel):
    """Customer creation DTO"""
    name: str = Field(..., description="Customer name 2-100 chars")
    address: str = Field(..., description="Address 5-255 chars")
    phone: str = Field(..., description="E.164 phone number")
    bankingDetails: BankingDetails = Field(..., description="Banking details")
    role: CustomerRole = Field(..., description="Customer role")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return validate_name(v)
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        return validate_address(v)
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        return validate_phone(v)

class Product(BaseModel):
    """Product entity"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="UUIDv4, server-generated")
    description: str = Field(..., description="Product description 3-500 chars")
    price: Price = Field(..., description="Product price")
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        return validate_product_description(v)

class ProductCreate(BaseModel):
    """Product creation DTO"""
    description: str = Field(..., description="Product description 3-500 chars")
    price: Price = Field(..., description="Product price")
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        return validate_product_description(v)

class Order(BaseModel):
    """Order entity"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="UUIDv4, server-generated")
    customerRef: str = Field(..., description="Customer UUID reference")
    lineItems: List[LineItem] = Field(..., description="Order line items")
    totalAmount: Optional[Decimal] = Field(None, description="Total amount (server-computed)")
    status: OrderStatus = Field(OrderStatus.PLACED, description="Order status")
    createdAt: Optional[str] = Field(None, description="Creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Last update timestamp")
    invoiceRef: Optional[str] = Field(None, description="Invoice UUID reference")
    
    @field_validator('customerRef')
    @classmethod
    def validate_customer_ref(cls, v):
        return validate_uuid_format(v)
    
    @field_validator('invoiceRef')
    @classmethod
    def validate_invoice_ref(cls, v):
        if v is not None:
            return validate_uuid_format(v)
        return v
class OrderCreate(BaseModel):
    """Order creation DTO"""
    customerRef: str = Field(..., description="Customer UUID reference")
    lineItems: List[LineItem] = Field(..., description="Order line items")
    
    @field_validator('customerRef')
    @classmethod
    def validate_customer_ref(cls, v):
        return validate_uuid_format(v)
    
    @model_validator(mode='after')
    def validate_line_items_count(self):
        """NFR 2.1: Validate line item count (1-100 items)"""
        if not self.lineItems or len(self.lineItems) < 1:
            raise ValueError("Order must have at least 1 line item")
        if len(self.lineItems) > 100:
            raise ValueError("Order cannot exceed 100 line items")
        return self

class OrderUpdate(BaseModel):
    """Order status update DTO"""
    status: OrderStatus = Field(..., description="New order status")

class Payment(BaseModel):
    """Payment entity"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="UUIDv4, server-generated")
    orderRef: str = Field(..., description="Order UUID reference")
    amount: Decimal = Field(..., description="Payment amount")
    timestamp: Optional[str] = Field(None, description="Payment timestamp")
    status: PaymentStatus = Field(PaymentStatus.PENDING, description="Payment status")
    method: PaymentMethod = Field(..., description="Payment method")
    
    @field_validator('orderRef')
    @classmethod
    def validate_order_ref(cls, v):
        return validate_uuid_format(v)

class PaymentCreate(BaseModel):
    """Payment creation DTO"""
    orderRef: str = Field(..., description="Order UUID reference")
    amount: Decimal = Field(..., description="Payment amount")
    method: PaymentMethod = Field(..., description="Payment method")
    
    @field_validator('orderRef')
    @classmethod
    def validate_order_ref(cls, v):
        return validate_uuid_format(v)
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        return validate_amount(v, Decimal('0.01'), Decimal('99999999.99'), 'Payment amount')

class PaymentVerify(BaseModel):
    """Payment verification DTO"""
    status: PaymentStatus = Field(..., description="Verification status")

class Invoice(BaseModel):
    """Invoice entity"""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    id: Optional[str] = Field(None, description="UUIDv4, server-generated")
    orderRef: str = Field(..., description="Order UUID reference")
    billingInfo: Dict[str, str] = Field(..., description="Billing information snapshot")
    totalAmount: Decimal = Field(..., description="Invoice total amount")
    issueDate: str = Field(..., description="Issue date dd/MM/yyyy")
    dueDate: str = Field(..., description="Due date dd/MM/yyyy")
    status: InvoiceStatus = Field(InvoiceStatus.ISSUED, description="Invoice status")
    
    @field_validator('orderRef')
    @classmethod
    def validate_order_ref(cls, v):
        return validate_uuid_format(v)
    
    @field_validator('issueDate')
    @classmethod
    def validate_issue_date(cls, v):
        return validate_date_ddmmyyyy(v, "Issue date")
    
    @field_validator('dueDate')
    @classmethod
    def validate_due_date(cls, v):
        return validate_date_ddmmyyyy(v, "Due date")

class InvoiceCreate(BaseModel):
    """Invoice creation DTO"""
    orderRef: str = Field(..., description="Order UUID reference")
    issueDate: Optional[str] = Field(None, description="Issue date dd/MM/yyyy")
    dueDate: Optional[str] = Field(None, description="Due date dd/MM/yyyy")
    
    @field_validator('orderRef')
    @classmethod
    def validate_order_ref(cls, v):
        return validate_uuid_format(v)
    
    @field_validator('issueDate')
    @classmethod
    def validate_issue_date(cls, v):
        if v is not None:
            return validate_date_ddmmyyyy(v, "Issue date")
        return v
    
    @field_validator('dueDate')
    @classmethod
    def validate_due_date(cls, v):
        if v is not None:
            return validate_date_ddmmyyyy(v, "Due date")
        return v

__all__ = [
    'CustomerRole', 'OrderStatus', 'PaymentStatus', 'PaymentMethod', 'InvoiceStatus',
    'BankingDetails', 'Price', 'LineItem',
    'Customer', 'CustomerCreate',
    'Product', 'ProductCreate',
    'Order', 'OrderCreate', 'OrderUpdate',
    'Payment', 'PaymentCreate', 'PaymentVerify',
    'Invoice', 'InvoiceCreate'
]
