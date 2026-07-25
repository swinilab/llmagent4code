"""
Product domain model with validation
"""
import re
from uuid import UUID, uuid4
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class Price(BaseModel):
    """Price with amount and currency"""
    amount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("999999.99"))
    currency: str = Field(..., min_length=3, max_length=3)
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        # Ensure exactly 2 decimal places
        if v.as_tuple().exponent != -2:
            raise ValueError("amount must have exactly 2 decimal places")
        return v
    
    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("currency must be 3 uppercase letters (ISO 4217)")
        return v


class Product(BaseModel):
    """Product entity model"""
    id: UUID = Field(default_factory=uuid4)
    description: str = Field(..., min_length=3, max_length=500)
    price: Price
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description cannot be blank or whitespace-only")
        return v
