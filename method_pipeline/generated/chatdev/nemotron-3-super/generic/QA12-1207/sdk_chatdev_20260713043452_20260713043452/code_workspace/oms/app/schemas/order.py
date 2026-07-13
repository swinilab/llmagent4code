from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .order_item import OrderItemInDB

class OrderBase(BaseModel):
    customer_id: int
    status: str

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[str] = None

class OrderInDBBase(OrderBase):
    id: int
    total_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Order(OrderInDBBase):
    items: List[OrderItemInDB] = []

class OrderWithItems(Order):
    pass