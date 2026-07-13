from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models import CustomerRole

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    banking_details: Optional[str] = None
    role: CustomerRole = CustomerRole.customer

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    banking_details: Optional[str] = None
    role: Optional[CustomerRole] = None

class CustomerInDBBase(CustomerBase):
    id: int
    order_history: Optional[str] = None  # simplified
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class CustomerInDB(CustomerInDBBase):
    pass

class CustomerResponse(CustomerInDBBase):
    pass