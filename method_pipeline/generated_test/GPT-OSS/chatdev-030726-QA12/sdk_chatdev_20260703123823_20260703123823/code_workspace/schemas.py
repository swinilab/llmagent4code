"""Pydantic schemas (shared domain models) for request/response validation.
These schemas are used both by API layer and can be shared with frontend.
"""

from datetime import datetime
from typing import List, Optional
import enum
from pydantic import BaseModel, Field

# Enums mirroring ORM enums for documentation
class RoleEnum(str, enum.Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ACCOUNTANT = "accountant"

class OrderStatusEnum(str, enum.Enum):
    CREATED = "created"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class InvoiceStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

# Customer schemas
class CustomerBase(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: Optional[str] = None
    role: RoleEnum = RoleEnum.CUSTOMER

    model_config = {"from_attributes": True}

class CustomerCreate(CustomerBase):
    pass

class CustomerRead(CustomerBase):
    id: int

# Product schemas
class ProductBase(BaseModel):
    description: str
    price: float
    currency: str = "USD"

    model_config = {"from_attributes": True}

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: int

# Order line item schemas
class OrderLineItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float

    model_config = {"from_attributes": True}

class OrderLineItemCreate(OrderLineItemBase):
    pass

class OrderLineItemRead(OrderLineItemBase):
    id: int

# Order schemas
class OrderBase(BaseModel):
    customer_id: int
    status: OrderStatusEnum = OrderStatusEnum.CREATED

    model_config = {"from_attributes": True}

class OrderCreate(OrderBase):
    line_items: List[OrderLineItemCreate]

class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    line_items: List[OrderLineItemRead]

# Payment schemas
class PaymentBase(BaseModel):
    order_id: int
    amount: float
    method: str
    status: PaymentStatusEnum = PaymentStatusEnum.PENDING

    model_config = {"from_attributes": True}

class PaymentCreate(PaymentBase):
    pass

class PaymentRead(PaymentBase):
    id: int
    timestamp: datetime

# Invoice schemas
class InvoiceBase(BaseModel):
    order_id: int
    billing_info: str
    amount: float
    due_date: Optional[datetime] = None
    status: InvoiceStatusEnum = InvoiceStatusEnum.DRAFT

    model_config = {"from_attributes": True}

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceRead(InvoiceBase):
    id: int
    issue_date: datetime
