"""
Pydantic schemas for Order entity.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from oms.models.enums import OrderStatus


class LineItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., gt=0)
    currency: str = "USD"


class OrderCreate(BaseModel):
    customer_id: str
    line_items: List[LineItemCreate] = Field(..., min_length=1)


class OrderUpdateStatus(BaseModel):
    status: OrderStatus


class LineItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: float
    currency: str

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    status: OrderStatus
    total_amount: float
    currency: str
    invoice_ref: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime
    line_items: List[LineItemResponse] = []

    model_config = {"from_attributes": True}
