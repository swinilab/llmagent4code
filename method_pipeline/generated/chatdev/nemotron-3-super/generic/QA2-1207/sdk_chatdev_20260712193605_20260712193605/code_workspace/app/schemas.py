from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models import UserRole, OrderStatus, PaymentStatus, InvoiceStatus

# User schemas
class UserBase(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    banking_details: Optional[str] = None
    role: Optional[UserRole] = None

class UserInDBBase(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserInDB(UserInDBBase):
    pass

# Product schemas
class ProductBase(BaseModel):
    description: str
    base_price: int  # in cents
    currency: str = "USD"

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    description: Optional[str] = None
    base_price: Optional[int] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class ProductInDBBase(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ProductInDB(ProductInDBBase):
    pass

# OrderItem schemas
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: int  # in cents
    total_price: int  # in cents

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[int] = None
    total_price: Optional[int] = None

class OrderItemInDBBase(OrderItemBase):
    id: int
    order_id: int

    class Config:
        orm_mode = True

class OrderItemInDB(OrderItemInDBBase):
    pass

# Order schemas
class OrderBase(BaseModel):
    customer_id: int
    status: OrderStatus
    total_amount: int  # in cents
    invoice_id: Optional[int] = None

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    total_amount: Optional[int] = None
    invoice_id: Optional[int] = None

class OrderInDBBase(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class OrderInDB(OrderInDBBase):
    items: List[OrderItemInDB] = []

# Payment schemas
class PaymentBase(BaseModel):
    order_id: int
    amount: int  # in cents
    method: str
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(PaymentBase):
    pass

class PaymentUpdate(BaseModel):
    amount: Optional[int] = None
    method: Optional[str] = None
    status: Optional[PaymentStatus] = None

class PaymentInDBBase(PaymentBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class PaymentInDB(PaymentInDBBase):
    pass

# Invoice schemas
class InvoiceBase(BaseModel):
    order_id: int
    billing_info: str
    amount: int  # in cents
    issue_date: datetime
    due_date: datetime
    status: InvoiceStatus = InvoiceStatus.DRAFT

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    order_id: Optional[int] = None
    billing_info: Optional[str] = None
    amount: Optional[int] = None
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None

class InvoiceInDBBase(InvoiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class InvoiceInDB(InvoiceInDBBase):
    pass