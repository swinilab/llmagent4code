from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.db.models import OrderStatus

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    line_total: float = Field(..., gt=0)

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None

class OrderItemInDBBase(OrderItemBase):
    id: int
    order_id: int

    class Config:
        orm_mode = True

class OrderItemInDB(OrderItemInDBBase):
    pass

class OrderItemResponse(OrderItemInDBBase):
    pass

class OrderBase(BaseModel):
    customer_id: int
    status: OrderStatus = OrderStatus.draft

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    status: Optional[OrderStatus] = None

class OrderInDBBase(OrderBase):
    id: int
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class OrderInDB(OrderInDBBase):
    pass

class OrderResponse(OrderInDBBase):
    items: List[OrderItemResponse] = []