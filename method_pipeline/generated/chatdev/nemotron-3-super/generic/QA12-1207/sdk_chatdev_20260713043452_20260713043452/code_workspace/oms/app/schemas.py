from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: str
    banking_details: Optional[str] = None
    role: str = Field(default="customer", max_length=50)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    banking_details: Optional[str] = None
    role: Optional[str] = None


class CustomerInDBBase(CustomerBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Customer(CustomerInDBBase):
    pass
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    sku: str
    is_active: Optional[bool] = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None


class ProductInDBBase(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Product(ProductInDBBase):
    pass


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    total_price: float


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None


class OrderItemInDBBase(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderItem(OrderItemInDBBase):
    pass


class OrderBase(BaseModel):
    customer_id: int
    order_number: str
    status: OrderStatusEnum = OrderStatusEnum.PENDING
    total_amount: float
    notes: Optional[str] = None
    is_active: Optional[bool] = True


class OrderCreate(OrderBase):
    order_items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    order_number: Optional[str] = None
    status: Optional[OrderStatusEnum] = None
    total_amount: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class OrderInDBBase(OrderBase):
    id: int
    order_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Order(OrderInDBBase):
    order_items: List[OrderItem] = []


class InvoiceBase(BaseModel):
    order_id: int
    invoice_number: str
    billing_info: str
    amount: float
    due_date: datetime
    status: Optional[str] = "issued"


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    order_id: Optional[int] = None
    invoice_number: Optional[str] = None
    billing_info: Optional[str] = None
    amount: Optional[float] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None


class InvoiceInDBBase(InvoiceBase):
    id: int
    issue_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Invoice(InvoiceInDBBase):
    pass


class PaymentBase(BaseModel):
    order_id: int
    amount: float
    payment_method: str
    transaction_id: str
    status: Optional[str] = "pending"


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    order_id: Optional[int] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    status: Optional[str] = None


class PaymentInDBBase(PaymentBase):
    id: int
    processed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Payment(PaymentInDBBase):
    pass


# Token schemas (not used now but placeholder)
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None