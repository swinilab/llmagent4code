"""
Pydantic schemas for Product.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    base_price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_price: float | None = None
    currency: str | None = None


class ProductResponse(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
