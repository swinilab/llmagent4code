"""
Pydantic schemas for Order.
"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.order import OrderStatus
from app.schemas.order_line_item import OrderLineItemRead
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentRead


class OrderBase(BaseModel):
    """Base order schema."""
    customer_id: int
    total_amount: float


class OrderCreate(OrderBase):
    """Order creation schema."""
    line_items: List[OrderLineItemRead]


class OrderRead(OrderBase):
    """Order read schema."""
    id: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    line_items: Optional[List[OrderLineItemRead]] = Field(default_factory=list)
    invoice: Optional[InvoiceRead] = None
    payment: Optional[PaymentRead] = None

    class Config:
        from_attributes = True