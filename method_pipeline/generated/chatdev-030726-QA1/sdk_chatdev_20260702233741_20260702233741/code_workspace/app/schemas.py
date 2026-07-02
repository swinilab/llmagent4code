from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator

class Role(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ACCOUNTANT = "accountant"

class OrderStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

# Shared schemas
class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    address: str
    phone: str = Field(..., max_length=50)
    banking_details: Optional[str] = None
    role: Role = Role.CUSTOMER

class CustomerCreate(CustomerBase):
    pass

class CustomerRead(CustomerBase):
    id: int

    class Config:
        orm_mode = True

class ProductBase(BaseModel):
    description: str
    base_price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: int

    class Config:
        orm_mode = True

class OrderLineItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)
    total_price: Decimal = Field(..., gt=0)

    @validator('total_price')
    def check_total(cls, v, values):
        if 'unit_price' in values and 'quantity' in values:
            expected = values['unit_price'] * values['quantity']
            if v != expected:
                raise ValueError('total_price must equal unit_price * quantity')
        return v

class OrderLineItemCreate(OrderLineItemBase):
    pass

class OrderLineItemRead(OrderLineItemBase):
    id: int

    class Config:
        orm_mode = True

class OrderBase(BaseModel):
    customer_id: int
    currency: str = Field(default="USD", max_length=3)

class OrderCreate(OrderBase):
    line_items: List[OrderLineItemCreate]

class OrderRead(BaseModel):
    id: int
    customer: CustomerRead
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    total_amount: Decimal
    currency: str
    line_items: List[OrderLineItemRead]
    invoice_id: Optional[int] = None

    class Config:
        orm_mode = True

class PaymentBase(BaseModel):
    order_id: int
    amount: Decimal = Field(..., gt=0)
    method: str = Field(..., max_length=50)
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(PaymentBase):
    pass

class PaymentRead(PaymentBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class InvoiceBase(BaseModel):
    order_id: int
    billing_info: str
    amount: Decimal = Field(..., gt=0)
    due_date: datetime
    status: InvoiceStatus = InvoiceStatus.DRAFT

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceRead(InvoiceBase):
    id: int
    issue_date: datetime

    class Config:
        orm_mode = True
