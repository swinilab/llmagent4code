"""
Domain models and Pydantic schemas for the Order Management System.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class OrderStatus(str, Enum):
    PENDING = "PENDING"       # Initial state
    ACCEPTED = "ACCEPTED"     # Reviewed by Order Staff
    INVOICED = "INVOICED"     # Invoice created by Accountant
    PAID = "PAID"             # Payment verified by Accountant
    SHIPPED = "SHIPPED"       # Shipped by Order Staff
    CLOSED = "CLOSED"         # Completed and closed

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class InvoiceStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    VOID = "VOID"

class Product(BaseModel):
    id: int
    description: str
    base_price: float
    currency: str = "USD"

class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float

class Customer(BaseModel):
    id: int
    name: str
    address: str
    phone: str
    banking_details: str
    role: str = "Customer"
    order_history: List[int] = [] # List of order IDs

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=5)
    banking_details: str = Field(..., min_length=1)
    role: str = "Customer"

class OrderBase(BaseModel):
    customer_id: int
    items: List[OrderItem]

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    total_amount: float
    status: OrderStatus

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float = Field(..., gt=0)
    method: str = Field(..., min_length=1)
    order_id: int

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    status: PaymentStatus
    timestamp: datetime

class InvoiceCreate(BaseModel):
    order_id: int
    billing_info: Optional[str] = None

class InvoiceResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    status: InvoiceStatus
    issue_date: datetime
    due_date: datetime
