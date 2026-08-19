import uuid
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


class Payment(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orderRef: str = Field(
        ...,
        description="Reference to Order.id (UUID), order must be in INVOICED status"
    )
    amount: str = Field(
        ...,
        pattern=r"^\d{1,8}\.\d{2}$",
        description="Payment amount: must exactly equal Invoice.totalAmount"
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        description="Payment status following state machine"
    )
    method: PaymentMethod
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("orderRef must be a valid UUIDv4")
        return v
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            amount_val = float(v)
        except ValueError:
            raise ValueError("amount must be a valid decimal")
        
        if amount_val < 0.01 or amount_val > 99999999.99:
            raise ValueError("amount must be between 0.01 and 99999999.99")
        
        if "." not in v or len(v.split(".")[1]) != 2:
            raise ValueError("amount must have exactly 2 decimal places")
        
        return v
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("id must be a valid UUIDv4")
        return v
