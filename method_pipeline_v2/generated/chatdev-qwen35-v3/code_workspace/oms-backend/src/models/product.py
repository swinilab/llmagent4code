import uuid
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Price(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    amount: str = Field(
        ...,
        pattern=r"^\d{1,6}\.\d{2}$",
        description="Price amount: 1-6 digits before decimal, exactly 2 decimal places, min 0.01, max 999999.99"
    )
    currency: Literal["USD", "VND", "EUR"] = Field(
        ...,
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 currency code"
    )
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        # Parse and validate numeric range
        try:
            amount_val = float(v)
        except ValueError:
            raise ValueError("amount must be a valid decimal")
        
        if amount_val < 0.01 or amount_val > 999999.99:
            raise ValueError("amount must be between 0.01 and 999999.99")
        
        # Ensure exactly 2 decimal places
        if "." not in v or len(v.split(".")[1]) != 2:
            raise ValueError("amount must have exactly 2 decimal places")
        
        return v


class Product(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Product description: 3-500 chars, must not be blank"
    )
    price: Price
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("description must not be blank or whitespace-only")
        return v
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("id must be a valid UUIDv4")
        return v
