"""
Product schemas — request and response models.
"""
import datetime as dt

from pydantic import BaseModel, Field, field_validator


class ProductBase(BaseModel):
    """Shared product fields."""
    description: str = Field(..., min_length=1)
    base_price: float = Field(..., gt=0, description="Base price before tax")
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""
    description: str | None = Field(default=None, min_length=1)
    base_price: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ProductRead(ProductBase):
    """Schema for reading a product."""
    id: str
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}