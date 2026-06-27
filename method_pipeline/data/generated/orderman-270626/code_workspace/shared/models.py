"""
Shared domain models for the Order Management System.
These models are used by both frontend and backend for consistent data handling.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User role enumeration for the system."""
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


class OrderStatus(str, Enum):
    """Order status enumeration representing the order lifecycle."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# ============================================================================
# Customer Domain Models
# ============================================================================

class CustomerBase(BaseModel):
    """Base customer model with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Customer full name")
    address: str = Field(..., min_length=1, max_length=500, description="Customer address")
    phone: str = Field(..., min_length=7, max_length=20, description="Customer phone number")
    email: str = Field(..., description="Customer email address")
    banking_details: Optional[str] = Field(None, max_length=500, description="Banking information")
    role: UserRole = Field(default=UserRole.CUSTOMER, description="User role in the system")


class CustomerCreate(CustomerBase):
    """Model for creating a new customer."""
    pass


class CustomerUpdate(BaseModel):
    """Model for updating customer information."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[str] = Field(None)
    banking_details: Optional[str] = Field(None, max_length=500)
    role: Optional[UserRole] = None


class Customer(CustomerBase):
    """Complete customer model with all fields."""
    id: int = Field(..., description="Unique customer identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    order_history: List[int] = Field(default_factory=list, description="List of order IDs")

    class Config:
        from_attributes = True


# ============================================================================
# Product Domain Models
# ============================================================================

class ProductBase(BaseModel):
    """Base product model with common fields."""
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str = Field(..., min_length=1, max_length=2000, description="Product description")
    price: float = Field(..., gt=0, description="Product price")
    sku: str = Field(..., min_length=1, max_length=50, description="Stock keeping unit")
    stock_quantity: int = Field(default=0, ge=0, description="Available stock quantity")


class ProductCreate(ProductBase):
    """Model for creating a new product."""
    pass


class ProductUpdate(BaseModel):
    """Model for updating product information."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    stock_quantity: Optional[int] = Field(None, ge=0)


class Product(ProductBase):
    """Complete product model with all fields."""
    id: int = Field(..., description="Unique product identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Order Domain Models
# ============================================================================

class OrderItem(BaseModel):
    """Model representing an item in an order."""
    product_id: int = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    unit_price: float = Field(..., gt=0, description="Price per unit")
    subtotal: float = Field(..., ge=0, description="Item subtotal")


class OrderBase(BaseModel):
    """Base order model with common fields."""
    customer_id: int = Field(..., description="Customer identifier")
    items: List[OrderItem] = Field(..., min_length=1, description="List of order items")
    total_amount: float = Field(..., ge=0, description="Total order amount")
    shipping_address: str = Field(..., min_length=1, max_length=500, description="Shipping address")
    notes: Optional[str] = Field(None, max_length=2000, description="Order notes")


class OrderCreate(OrderBase):
    """Model for creating a new order."""
    pass


class OrderUpdate(BaseModel):
    """Model for updating order information."""
    status: Optional[OrderStatus] = None
    shipping_address: Optional[str] = Field(None, min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)


class Order(OrderBase):
    """Complete order model with all fields."""
    id: int = Field(..., description="Unique order identifier")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Current order status")
    invoice_id: Optional[int] = Field(None, description="Associated invoice ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Order creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    accepted_at: Optional[datetime] = Field(None, description="Order acceptance timestamp")
    shipped_at: Optional[datetime] = Field(None, description="Order shipping timestamp")
    completed_at: Optional[datetime] = Field(None, description="Order completion timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Invoice Domain Models
# ============================================================================

class InvoiceBase(BaseModel):
    """Base invoice model with common fields."""
    order_id: int = Field(..., description="Associated order identifier")
    customer_id: int = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Invoice amount")
    due_date: datetime = Field(..., description="Payment due date")
    billing_address: str = Field(..., min_length=1, max_length=500, description="Billing address")


class InvoiceCreate(InvoiceBase):
    """Model for creating a new invoice."""
    pass


class InvoiceUpdate(BaseModel):
    """Model for updating invoice information."""
    status: Optional[InvoiceStatus] = None
    amount: Optional[float] = Field(None, gt=0)
    due_date: Optional[datetime] = None
    billing_address: Optional[str] = Field(None, min_length=1, max_length=500)


class Invoice(InvoiceBase):
    """Complete invoice model with all fields."""
    id: int = Field(..., description="Unique invoice identifier")
    invoice_number: str = Field(..., description="Human-readable invoice number")
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, description="Current invoice status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Payment Domain Models
# ============================================================================

class PaymentBase(BaseModel):
    """Base payment model with common fields."""
    invoice_id: int = Field(..., description="Associated invoice identifier")
    customer_id: int = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., min_length=1, max_length=100, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=200, description="Transaction reference")


class PaymentCreate(PaymentBase):
    """Model for creating a new payment."""
    pass


class PaymentUpdate(BaseModel):
    """Model for updating payment information."""
    status: Optional[PaymentStatus] = None
    amount: Optional[float] = Field(None, gt=0)
    transaction_id: Optional[str] = Field(None, max_length=200)


class Payment(PaymentBase):
    """Complete payment model with all fields."""
    id: int = Field(..., description="Unique payment identifier")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Current payment status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    processed_at: Optional[datetime] = Field(None, description="Payment processing timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Response Models for API
# ============================================================================

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = ""
    data: Optional[dict] = None


class CustomerListResponse(BaseModel):
    """Response model for customer list."""
    customers: List[Customer]
    total: int


class OrderListResponse(BaseModel):
    """Response model for order list."""
    orders: List[Order]
    total: int


class ProductListResponse(BaseModel):
    """Response model for product list."""
    products: List[Product]
    total: int


class InvoiceListResponse(BaseModel):
    """Response model for invoice list."""
    invoices: List[Invoice]
    total: int


class PaymentListResponse(BaseModel):
    """Response model for payment list."""
    payments: List[Payment]
    total: int
