"""
Pydantic schemas for Customer API.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=50)
    banking_details: str = Field(..., min_length=1)
    role: UserRole = UserRole.CUSTOMER


class CustomerResponse(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    customers: list[CustomerResponse]
    total: int
