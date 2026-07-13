from pydantic import BaseModel
from typing import Optional, List

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

    class Config:
        orm_mode = True

class ProductInDB(ProductInDBBase):
    pass

class Product(ProductInDBBase):
    pass

class ProductResponse(ProductInDBBase):
    pass

class ProductList(BaseModel):
    items: List[Product]
    total: int
    page: int
    size: int