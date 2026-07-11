"""
Pydantic schemas for Order and OrderLineItem entities.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.enums import OrderStatus


class OrderLineItemCreate(BaseModel):
    product_id: str = Field(..., min_length=1)
    product_description: str = Field(..., min_length=1, max_length=1000)
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., ge=0)
    currency: str = "USD"


class OrderLineItemRead(BaseModel):
    id: str
    order_id: str
    product_id: str
    product_description: str
    quantity: int
    unit_price: Decimal
    currency: str
    line_total: Decimal

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: str = Field(..., min_length=1)
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=2000)


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    notes: Optional[str] = Field(None, max_length=2000)
    invoice_ref: Optional[str] = None


class OrderRead(BaseModel):
    id: str
    customer_id: str
    status: OrderStatus
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    currency: str
    invoice_ref: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    line_items: List[OrderLineItemRead] = []

    model_config = {"from_attributes": True}
