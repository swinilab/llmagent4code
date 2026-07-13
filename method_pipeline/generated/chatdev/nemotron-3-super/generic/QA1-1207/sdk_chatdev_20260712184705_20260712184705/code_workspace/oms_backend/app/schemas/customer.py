from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CustomerBase(BaseModel):
    name: str
    address: str
    phone: str
    banking_details: str
    role: str

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    banking_details: Optional[str] = None
    role: Optional[str] = None

class CustomerInDBBase(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class CustomerInDB(CustomerInDBBase):
    pass

class Customer(CustomerInDBBase):
    pass

class CustomerResponse(CustomerInDBBase):
    pass

class CustomerList(BaseModel):
    items: List[Customer]
    total: int
    page: int
    size: int