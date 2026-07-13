from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    description: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None

class ProductInDBBase(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ProductInDB(ProductInDBBase):
    pass

class ProductResponse(ProductInDBBase):
    pass