"""
Pydantic schemas for Order and OrderItem.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.order import OrderStatus


class OrderItemBase(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: str
    order_id: str
    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    customer_id: str
    currency: str = Field(default="USD", max_length=3)


class OrderCreate(OrderBase):
    line_items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderResponse(OrderBase):
    id: str
    status: OrderStatus
    total_amount: float
    invoice_ref: str | None
    created_at: datetime
    updated_at: datetime
    line_items: list[OrderItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
