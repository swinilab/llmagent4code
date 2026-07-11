"""
Pydantic schemas for request/response validation.

Provides data transfer objects (DTOs) for API endpoints with proper validation.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class OrderStatus(str, Enum):
    """Order lifecycle status enum."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# ============== Customer Schemas ==============

class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255, description="Customer full name")
    email: EmailStr = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, max_length=50, description="Customer phone number")
    address: Optional[str] = Field(None, description="Customer shipping/billing address")
    banking_details: Optional[str] = Field(None, max_length=1024, description="Encrypted banking information")


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    banking_details: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool


# ============== Product Schemas ==============

class ProductCreate(BaseModel):
    """Schema for creating a new product."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    base_price: Decimal = Field(..., gt=0, description="Base price")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    stock_quantity: int = Field(default=0, ge=0, description="Available stock")


class ProductResponse(BaseModel):
    """Schema for product response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    base_price: Decimal
    currency: str
    stock_quantity: int
    is_available: bool
    created_at: datetime
    updated_at: datetime


# ============== Order Schemas ==============

class OrderLineItemCreate(BaseModel):
    """Schema for creating an order line item."""
    model_config = ConfigDict(from_attributes=True)
    
    product_id: int = Field(..., gt=0, description="Product ID")
    quantity: int = Field(..., gt=0, description="Item quantity")


class OrderCreate(BaseModel):
    """Schema for creating a new order."""
    model_config = ConfigDict(from_attributes=True)
    
    customer_id: int = Field(..., gt=0, description="Customer ID")
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1, description="Order line items")
    shipping_address: Optional[str] = Field(None, description="Shipping address")
    notes: Optional[str] = Field(None, description="Order notes")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")


class OrderLineItemResponse(BaseModel):
    """Schema for order line item response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product: Optional[ProductResponse] = None


class OrderResponse(BaseModel):
    """Schema for order response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    customer_id: int
    status: OrderStatus
    total_amount: Decimal
    currency: str
    shipping_address: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    shipped_at: Optional[datetime]
    completed_at: Optional[datetime]
    invoice_id: Optional[int]
    line_items: List[OrderLineItemResponse]
    customer: Optional[CustomerResponse] = None


class OrderUpdateStatus(BaseModel):
    """Schema for updating order status."""
    model_config = ConfigDict(from_attributes=True)
    
    status: OrderStatus = Field(..., description="New order status")
    notes: Optional[str] = Field(None, description="Optional notes for status change")


# ============== Payment Schemas ==============

class PaymentCreate(BaseModel):
    """Schema for creating a new payment."""
    model_config = ConfigDict(from_attributes=True)
    
    order_id: int = Field(..., gt=0, description="Order ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    method: str = Field(..., min_length=1, max_length=50, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=255, description="External transaction ID")


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_id: int
    amount: Decimal
    currency: str
    method: str
    status: PaymentStatus
    transaction_id: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime


# ============== Invoice Schemas ==============

class InvoiceCreate(BaseModel):
    """Schema for creating a new invoice."""
    model_config = ConfigDict(from_attributes=True)
    
    order_id: int = Field(..., gt=0, description="Order ID")
    billing_name: str = Field(..., min_length=1, max_length=255, description="Billing contact name")
    billing_address: Optional[str] = Field(None, description="Billing address")
    tax_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=1, description="Tax rate (0-1)")
    due_date: datetime = Field(..., description="Invoice due date")


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    order_id: int
    invoice_number: str
    billing_name: str
    billing_address: Optional[str]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    issue_date: datetime
    due_date: datetime
    status: InvoiceStatus
    created_at: datetime
    updated_at: datetime


# ============== Common Response Schemas ==============

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Schema for error response."""
    error: str
    message: str
    details: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Schema for paginated response."""
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
