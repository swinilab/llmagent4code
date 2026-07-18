"""
Order schemas — request and response models including line items.
"""
import datetime as dt

from pydantic import BaseModel, Field, model_validator

from oms.enums import OrderStatus
from oms.schemas.invoice import InvoiceRead
from oms.schemas.payment import PaymentRead


class OrderLineItemCreate(BaseModel):
    """Schema for creating a line item."""
    product_id: str
    quantity: int = Field(..., ge=1)


class OrderLineItemRead(BaseModel):
    """Schema for reading a line item."""
    id: str
    order_id: str
    product_id: str
    quantity: int
    unit_price: float
    currency: str

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    """Schema for creating an order."""
    customer_id: str
    items: list[OrderLineItemCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> "OrderCreate":
        seen = set()
        for item in self.items:
            if item.product_id in seen:
                raise ValueError(f"Duplicate product_id {item.product_id} in order")
            seen.add(item.product_id)
        return self


class OrderUpdate(BaseModel):
    """Schema for updating an order (add/remove items). Only valid when PENDING."""
    items: list[OrderLineItemCreate] = Field(..., min_length=1)


class OrderStatusUpdate(BaseModel):
    """Schema for transitioning order status."""
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)


class OrderRead(BaseModel):
    """Schema for reading an order with all nested data."""
    id: str
    customer_id: str
    status: OrderStatus
    subtotal: float
    tax: float
    total: float
    currency: str
    created_at: dt.datetime
    updated_at: dt.datetime
    accepted_at: dt.datetime | None = None
    shipped_at: dt.datetime | None = None
    closed_at: dt.datetime | None = None
    invoice_id: str | None = None
    line_items: list[OrderLineItemRead] = Field(default_factory=list)
    invoice: InvoiceRead | None = None
    payments: list[PaymentRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}