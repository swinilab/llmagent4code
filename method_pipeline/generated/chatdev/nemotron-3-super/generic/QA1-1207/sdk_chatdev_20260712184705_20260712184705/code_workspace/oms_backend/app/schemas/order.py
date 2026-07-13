from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum as PyEnum
from oms_backend.app.schemas.order_item import OrderItemCreate


class OrderStatus(str, PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class OrderBase(BaseModel):
    customer_id: int
    status: OrderStatus = OrderStatus.PENDING


class OrderCreate(OrderBase):
    pass


class OrderCreateWithItems(OrderBase):
    items: List[OrderItemCreate] = []


class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[OrderStatus] = None


class OrderInDBBase(OrderBase):
    id: int
    total_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class OrderInDB(OrderInDBBase):
    pass


class Order(OrderInDBBase):
    pass


class OrderList(BaseModel):
    items: List[Order]
    total: int
    page: int
    size: int