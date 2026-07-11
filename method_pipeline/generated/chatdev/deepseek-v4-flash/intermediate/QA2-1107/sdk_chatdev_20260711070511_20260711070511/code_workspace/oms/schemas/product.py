"""
Pydantic schemas for Product entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    description: str = Field(..., min_length=1)
    base_price: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class ProductUpdate(BaseModel):
    description: Optional[str] = None
    base_price: Optional[float] = None
    currency: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    description: str
    base_price: float
    currency: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
