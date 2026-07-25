"""
Order domain model with validation
"""
import re
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class OrderStatus:
    """Order status enumeration with lifecycle"""
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    
    ALLOWED = [PLACED, ACCEPTED, INVOICED, PAID, VERIFIED, SHIPPED, CLOSED, CANCELLED]
    
    # Valid state transitions
    TRANSITIONS = {
        PLACED: [ACCEPTED, CANCELLED],
        ACCEPTED: [INVOICED, CANCELLED],
        INVOICED: [PAID, CANCELLED],
        PAID: [VERIFIED],
        VERIFIED: [SHIPPED],
        SHIPPED: [CLOSED],
        CLOSED: [],
        CANCELLED: [],
    }


class LineItem(BaseModel):
    """Line item in an order"""
    productRef: UUID
    quantity: int = Field(..., ge=1, le=1000)
    unitPriceSnapshot: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("999999.99"))
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError("quantity must be between 1 and 1000")
        return v
    
    @field_validator("unitPriceSnapshot")
    @classmethod
    def validate_unit_price(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent != -2:
            raise ValueError("unitPriceSnapshot must have exactly 2 decimal places")
        return v


class Order(BaseModel):
    """Order entity model"""
    id: UUID = Field(default_factory=uuid4)
    customerRef: UUID
    lineItems: List[LineItem] = Field(..., min_length=1, max_length=100)
    totalAmount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("99999999.99"))
    status: str = Field(default=OrderStatus.PLACED)
    createdAt: datetime = Field(default_factory=lambda: datetime.utcnow())
    updatedAt: datetime = Field(default_factory=lambda: datetime.utcnow())
    invoiceRef: Optional[UUID] = None
    
    @field_validator("lineItems")
    @classmethod
    def validate_line_items(cls, v: List[LineItem]) -> List[LineItem]:
        if len(v) < 1:
            raise ValueError("order must have at least 1 line item")
        if len(v) > 100:
            raise ValueError("order cannot have more than 100 line items")
        
        # Check for duplicate productRef
        product_refs = [item.productRef for item in v]
        if len(product_refs) != len(set(product_refs)):
            raise ValueError("duplicate productRef in line items not allowed")
        
        return v
    
    @field_validator("totalAmount")
    @classmethod
    def validate_total_amount(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent != -2:
            raise ValueError("totalAmount must have exactly 2 decimal places")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in OrderStatus.ALLOWED:
            raise ValueError(f"status must be one of {OrderStatus.ALLOWED}")
        return v
    
    @model_validator(mode="after")
    def validate_timestamps(self) -> "Order":
        if self.updatedAt < self.createdAt:
            raise ValueError("updatedAt must be >= createdAt")
        return self
    
    @classmethod
    def compute_total(cls, line_items: List[LineItem]) -> Decimal:
        """Compute total amount from line items"""
        total = Decimal("0.00")
        for item in line_items:
            total += item.quantity * item.unitPriceSnapshot
        return total.quantize(Decimal("0.01"))
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if status transition is valid"""
        if from_status not in OrderStatus.TRANSITIONS:
            return False
        return to_status in OrderStatus.TRANSITIONS[from_status]
