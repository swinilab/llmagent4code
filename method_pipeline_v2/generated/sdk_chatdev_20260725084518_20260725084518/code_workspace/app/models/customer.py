"""
Customer domain model with validation
"""
import re
from uuid import UUID, uuid4
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CustomerRole:
    """Customer role enumeration"""
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"
    
    ALLOWED = [CUSTOMER, ORDER_STAFF, ACCOUNTANT]


class BankingDetails(BaseModel):
    """Banking details for customer"""
    accountNumber: str = Field(..., min_length=6, max_length=20)
    bankName: str = Field(..., min_length=2, max_length=100)
    
    @field_validator("accountNumber")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        if not re.match(r"^\d{6,20}$", v):
            raise ValueError("accountNumber must be 6-20 digits only")
        return v
    
    @field_validator("bankName")
    @classmethod
    def validate_bank_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9 .&-]+$", v, flags=re.UNICODE):
            raise ValueError("bankName contains invalid characters")
        if not v.strip():
            raise ValueError("bankName cannot be blank")
        return v

class Customer(BaseModel):
    """Customer entity model"""
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=8, max_length=15)
    bankingDetails: BankingDetails
    role: str = Field(default=CustomerRole.CUSTOMER)
    orderHistory: List[UUID] = Field(default_factory=list)
    
    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be blank or whitespace-only")
        # Check that all characters are letters (Unicode), spaces, dots, apostrophes, or hyphens
        for char in v:
            if not (char.isalpha() or char in " .'-"):
                raise ValueError("name contains invalid characters")
        return v
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("address cannot be blank or whitespace-only")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^\+?[1-9]\d{7,14}$", v):
            raise ValueError("phone must be in E.164 format (8-15 digits, no leading 0)")
        return v
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in CustomerRole.ALLOWED:
            raise ValueError(f"role must be one of {CustomerRole.ALLOWED}")
        return v
    
    class Config:
        use_enum_values = True
