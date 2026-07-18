"""
Pydantic schemas for Order Line Item.
"""
from pydantic import BaseModel


class OrderLineItemBase(BaseModel):
    """Base order line item schema."""
    product_id: int
    quantity: int
    unit_price: float
    total_price: float


class OrderLineItemCreate(OrderLineItemBase):
    """Order line item creation schema."""
    product_id: int
    quantity: int
    price: float


class OrderLineItemRead(OrderLineItemBase):
    """Order line item read schema."""
    id: int

    class Config:
        from_attributes = True