"""
Pydantic schemas for Product.
"""
from pydantic import BaseModel


class ProductBase(BaseModel):
    """Base product schema."""
    description: str
    base_price: float
    currency: str


class ProductCreate(ProductBase):
    """Product creation schema."""
    description: str
    base_price: float
    currency: str = "USD"


class ProductRead(ProductBase):
    """Product read schema."""
    id: int

    class Config:
        from_attributes = True