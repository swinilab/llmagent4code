"""
Pydantic schemas for Order API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str = ""
    quantity: int
    unit_price: float
    total_price: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str = ""
    invoice_id: str | None = None
    status: OrderStatus
    total_amount: float
    currency: str
    line_items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
