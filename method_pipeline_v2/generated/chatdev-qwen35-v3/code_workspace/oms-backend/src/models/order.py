import uuid
import re
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class LineItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    productRef: str = Field(
        ...,
        description="Reference to Product.id (UUID)"
    )
    quantity: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Quantity: 1-1000, whole number"
    )
    unitPriceSnapshot: str = Field(
        ...,
        pattern=r"^\d{1,6}\.\d{2}$",
        description="Unit price snapshot at order time: exactly 2 decimal places"
    )
    
    @field_validator("productRef")
    @classmethod
    def validate_product_ref(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("productRef must be a valid UUIDv4")
        return v
    
    @field_validator("unitPriceSnapshot")
    @classmethod
    def validate_unit_price_snapshot(cls, v: str) -> str:
        try:
            amount_val = float(v)
        except ValueError:
            raise ValueError("unitPriceSnapshot must be a valid decimal")
        
        if amount_val < 0.01 or amount_val > 999999.99:
            raise ValueError("unitPriceSnapshot must be between 0.01 and 999999.99")
        
        if "." not in v or len(v.split(".")[1]) != 2:
            raise ValueError("unitPriceSnapshot must have exactly 2 decimal places")
        
        return v


class Order(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customerRef: str = Field(
        ...,
        description="Reference to Customer.id (UUID)"
    )
    lineItems: List[LineItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Line items: 1-100 items"
    )
    totalAmount: str = Field(
        ...,
        pattern=r"^\d{1,8}\.\d{2}$",
        description="Total amount: server-computed, sum of (quantity * unitPriceSnapshot)"
    )
    status: OrderStatus = Field(
        default=OrderStatus.PLACED,
        description="Order status following state machine"
    )
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updatedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    invoiceRef: Optional[str] = Field(None, description="Reference to Invoice.id (UUID), null until invoiced")
    
    @field_validator("customerRef")
    @classmethod
    def validate_customer_ref(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("customerRef must be a valid UUIDv4")
        return v
    
    @field_validator("totalAmount")
    @classmethod
    def validate_total_amount(cls, v: str) -> str:
        try:
            amount_val = float(v)
        except ValueError:
            raise ValueError("totalAmount must be a valid decimal")
        
        if amount_val < 0.01 or amount_val > 99999999.99:
            raise ValueError("totalAmount must be between 0.01 and 99999999.99")
        
        if "." not in v or len(v.split(".")[1]) != 2:
            raise ValueError("totalAmount must have exactly 2 decimal places")
        
        return v
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("id must be a valid UUIDv4")
        return v
    
    @field_validator("invoiceRef")
    @classmethod
    def validate_invoice_ref(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                uuid.UUID(v, version=4)
            except ValueError:
                raise ValueError("invoiceRef must be a valid UUIDv4")
        return v
    
    @model_validator(mode="after")
    def validate_line_items_no_duplicates(self) -> "Order":
        product_refs = [item.productRef for item in self.lineItems]
        if len(product_refs) != len(set(product_refs)):
            raise ValueError("lineItems must not contain duplicate productRef values")
        return self
    
    @model_validator(mode="after")
    def validate_total_amount_computed(self) -> "Order":
        # Server-side computation of totalAmount
        computed_total = 0.0
        for item in self.lineItems:
            computed_total += item.quantity * float(item.unitPriceSnapshot)
        
        computed_total_str = f"{computed_total:.2f}"
        
        # For creation, we set it; for updates, we validate it matches
        if hasattr(self, "totalAmount") and self.totalAmount:
            if self.totalAmount != computed_total_str:
                raise ValueError(f"totalAmount must equal sum of (quantity * unitPriceSnapshot). Expected {computed_total_str}, got {self.totalAmount}")
        else:
            object.__setattr__(self, "totalAmount", computed_total_str)
        
        return self
    
    @model_validator(mode="after")
    def validate_timestamps(self) -> "Order":
        # Ensure updatedAt >= createdAt
        if self.createdAt and self.updatedAt:
            created = datetime.fromisoformat(self.createdAt.replace("Z", "+00:00"))
            updated = datetime.fromisoformat(self.updatedAt.replace("Z", "+00:00"))
            if updated < created:
                raise ValueError("updatedAt must be >= createdAt")
        return self
