"""
Pydantic schemas for Product.
"""

from pydantic import BaseModel, Field
from typing import Optional

class ProductBase(BaseModel):
    description: str
    base_price: float
    currency: str = "USD"

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    description: Optional[str] = None
    base_price: Optional[float] = None
    currency: Optional[str] = None

class ProductOut(ProductBase):
    id: int

    class Config:
        orm_mode = True
