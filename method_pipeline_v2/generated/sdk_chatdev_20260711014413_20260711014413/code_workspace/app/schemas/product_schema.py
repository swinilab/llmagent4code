"""
Pydantic schemas for Product API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    base_price: float = Field(..., gt=0)
    currency: str = "USD"
    stock_quantity: int = Field(default=0, ge=0)


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    base_price: float
    currency: str
    stock_quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductSearchResponse(BaseModel):
    products: list[ProductResponse]
    total: int
    page: int
    size: int
