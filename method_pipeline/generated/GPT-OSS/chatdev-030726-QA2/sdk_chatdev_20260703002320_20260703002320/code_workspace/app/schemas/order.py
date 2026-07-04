"""
Pydantic schemas for Order and OrderLineItem.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PLACED = "placed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"

class OrderLineItemBase(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: float

class OrderLineItemCreate(OrderLineItemBase):
    pass

class OrderLineItemOut(OrderLineItemBase):
    id: int
    class Config:
        orm_mode = True

class OrderBase(BaseModel):
    customer_id: int
    status: OrderStatus = OrderStatus.PLACED
    total_amount: float = 0.0

class OrderCreate(OrderBase):
    line_items: List[OrderLineItemCreate]

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    total_amount: Optional[float] = None

class OrderOut(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    line_items: List[OrderLineItemOut] = []
    class Config:
        orm_mode = True
