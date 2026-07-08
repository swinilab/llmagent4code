"""
Pydantic schemas for Customer.
"""
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: str = Field(default="customer", max_length=50)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    banking_details: str | None = None
    role: str | None = None


class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
