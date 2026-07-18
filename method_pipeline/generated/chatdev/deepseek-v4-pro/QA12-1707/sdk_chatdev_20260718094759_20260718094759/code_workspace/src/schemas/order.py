"""Order schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item within an order."""

    product_id: str
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)


class OrderCreate(BaseModel):
    """Payload to place an order."""

    customer_id: str
    line_items: list[LineItem] = Field(..., min_length=1)
    tax: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class OrderStatusUpdate(BaseModel):
    """Payload to transition order status."""

    status: str = Field(
        ..., pattern=r"^(pending|accepted|invoiced|paid|shipped|closed|cancelled)$"
    )


class OrderResponse(BaseModel):
    """Order as returned by the API."""

    id: str
    customer_id: str
    line_items: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str
    invoice_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
