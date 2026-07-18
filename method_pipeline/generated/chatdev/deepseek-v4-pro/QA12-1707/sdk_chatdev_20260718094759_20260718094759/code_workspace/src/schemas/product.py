"""Product schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Payload to create a product."""

    description: str = Field(..., min_length=1)
    base_price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class ProductUpdate(BaseModel):
    """Partial update for a product."""

    description: str | None = Field(default=None, min_length=1)
    base_price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ProductResponse(BaseModel):
    """Product as returned by the API."""

    id: str
    description: str
    base_price: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
