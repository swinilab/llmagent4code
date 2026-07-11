"""
Pydantic schemas for Product entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    pricing: dict = Field(default_factory=lambda: {"base_price": 0.0, "currency": "USD"})


class ProductUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    pricing: Optional[dict] = None


class ProductRead(BaseModel):
    id: str
    description: str
    pricing: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
