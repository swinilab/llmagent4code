"""
Pydantic schemas for Customer entity.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from oms.models.enums import UserRole


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: UserRole = UserRole.CUSTOMER


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    banking_details: Optional[str] = None
    role: Optional[UserRole] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
