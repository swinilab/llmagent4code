"""DTOs for Order entity – strict validation per Field Constraint Table.
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import List

class LineItemDTO(BaseModel):
    productRef: str = Field(..., min_length=36, max_length=36, pattern=r"^[0-9a-fA-F-]{36}$")
    quantity: int = Field(..., ge=1, le=1000)
    unitPriceSnapshot: str = Field(..., pattern=r"^\d{1,6}\.\d{2}$")

    @validator("unitPriceSnapshot")
    def price_range(cls, v: str) -> str:
        val = float(v)
        if not (0.01 <= val <= 999999.99):
            raise ValueError("unitPriceSnapshot out of range")
        return v

class OrderCreateDTO(BaseModel):
    customerRef: str = Field(..., min_length=36, max_length=36, pattern=r"^[0-9a-fA-F-]{36}$")
    lineItems: List[LineItemDTO] = Field(..., min_items=1, max_items=100)

    @root_validator
    def no_duplicate_products(cls, values):
        items = values.get("lineItems", [])
        refs = [i.productRef for i in items]
        if len(set(refs)) != len(refs):
            raise ValueError("Duplicate productRef in line items")
        return values

class OrderResponseDTO(BaseModel):
    id: str
    customerRef: str
    lineItems: List[LineItemDTO]
    totalAmount: str
    status: str
    createdAt: str
    updatedAt: str
    invoiceRef: str | None = None
