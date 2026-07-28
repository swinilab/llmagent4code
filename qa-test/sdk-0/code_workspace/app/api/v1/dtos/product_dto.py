"""Pydantic DTOs for Product entity – validation follows the Field Constraint Table.
"""

from pydantic import BaseModel, Field, validator
from typing import Literal

class PriceDTO(BaseModel):
    amount: str = Field(..., pattern=r"^\d{1,6}\.\d{2}$")
    currency: Literal["USD", "VND", "EUR"]

    @validator("amount")
    def amount_range(cls, v: str) -> str:
        # Ensure numeric range 0.01 – 999999.99
        val = float(v)
        if not (0.01 <= val <= 999999.99):
            raise ValueError("price.amount out of allowed range")
        return v

class ProductResponseDTO(BaseModel):
    id: str = Field(..., min_length=36, max_length=36, pattern=r"^[0-9a-fA-F-]{36}$")
    description: str = Field(..., min_length=3, max_length=500)
    price: PriceDTO
