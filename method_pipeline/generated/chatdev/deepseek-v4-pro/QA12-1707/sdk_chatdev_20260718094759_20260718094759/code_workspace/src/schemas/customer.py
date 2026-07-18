"""Customer schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Payload to create a customer."""

    name: str = Field(..., min_length=1, max_length=200)
    address: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1, max_length=30)
    banking_details: str = Field(default="")
    role: str = Field(default="customer", pattern=r"^(customer|staff|accountant)$")


class CustomerUpdate(BaseModel):
    """Partial update for a customer."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    banking_details: str | None = None
    role: str | None = Field(default=None, pattern=r"^(customer|staff|accountant)$")


class CustomerResponse(BaseModel):
    """Customer as returned by the API."""

    id: str
    name: str
    address: str
    phone: str
    banking_details: str
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
