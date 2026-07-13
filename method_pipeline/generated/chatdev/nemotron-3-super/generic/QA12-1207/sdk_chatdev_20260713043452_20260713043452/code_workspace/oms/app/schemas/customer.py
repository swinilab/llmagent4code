from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    address: str = Field(...)
    phone: Optional[str] = Field(None, max_length=50)
    banking_details: Optional[str] = None
    role: str = Field(default="customer", max_length=50)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    banking_details: Optional[str] = None
    role: Optional[str] = Field(None, max_length=50)

class CustomerInDBBase(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CustomerInDB(CustomerInDBBase):
    pass

class Customer(CustomerInDBBase):
    pass