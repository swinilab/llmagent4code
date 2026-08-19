import uuid
import re
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CustomerRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class BankingDetails(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    accountNumber: str = Field(
        ...,
        min_length=6,
        max_length=20,
        pattern=r"^\d{6,20}$",
        description="Account number: 6-20 digits"
    )
    bankName: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[\p{L}0-9 .&-]+$",
        description="Bank name: 2-100 chars, letters, digits, spaces, dots, ampersand, hyphen"
    )
    
    @field_validator("bankName")
    @classmethod
    def validate_bank_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("bankName must not be blank or whitespace-only")
        # Unicode letter check
        if not re.match(r"^[\p{L}0-9 .&-]+$", v, re.UNICODE):
            raise ValueError("bankName contains invalid characters")
        return v


class Customer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[\p{L} .'-]+$",
        description="Customer name: 2-100 chars, Unicode letters, spaces, dots, apostrophes, hyphens"
    )
    address: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Customer address: 5-255 chars"
    )
    phone: str = Field(
        ...,
        min_length=8,
        max_length=15,
        pattern=r"^\+?[1-9]\d{7,14}$",
        description="Phone in E.164 format: 8-15 digits, optional leading +, must not start with 0 after country code"
    )
    bankingDetails: BankingDetails
    role: CustomerRole = Field(..., description="Role fixed at creation")
    orderHistory: List[str] = Field(default_factory=list, description="Array of order UUIDs, read-only")
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be blank or whitespace-only")
        # Validate Unicode letters pattern
        if not re.match(r"^[\p{L} .'-]+$", v, re.UNICODE):
            raise ValueError("name contains invalid characters, must only contain Unicode letters, spaces, dots, apostrophes, hyphens")
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("address must not be blank or whitespace-only")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # E.164 format: +[country code][number], no leading 0 after country code
        if not re.match(r"^\+?[1-9]\d{7,14}$", v):
            raise ValueError("phone must be in E.164 format: 8-15 digits, optional leading +, must not start with 0 after country code")
        return v
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("id must be a valid UUIDv4")
        return v
