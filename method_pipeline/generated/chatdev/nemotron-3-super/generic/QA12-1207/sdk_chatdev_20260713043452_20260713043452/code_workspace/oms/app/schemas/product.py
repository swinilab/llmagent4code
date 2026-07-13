from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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

class ProductInDBBase(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Product(ProductInDBBase):
    pass