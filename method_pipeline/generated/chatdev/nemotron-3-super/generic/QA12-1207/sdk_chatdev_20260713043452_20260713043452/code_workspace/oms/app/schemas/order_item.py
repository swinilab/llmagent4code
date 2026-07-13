from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    total_price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemUpdate(OrderItemBase):
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None

class OrderItemInDBBase(OrderItemBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True

class OrderItemInDB(OrderItemInDBBase):
    pass