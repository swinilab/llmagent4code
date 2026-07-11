"""
Pydantic schemas for Customer entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.enums import CustomerRole


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=500)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: dict = Field(default_factory=dict)
    role: CustomerRole = CustomerRole.CUSTOMER


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    phone: Optional[str] = Field(None, min_length=1, max_length=50)
    banking_details: Optional[dict] = None
    role: Optional[CustomerRole] = None


class CustomerRead(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: dict
    role: CustomerRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
