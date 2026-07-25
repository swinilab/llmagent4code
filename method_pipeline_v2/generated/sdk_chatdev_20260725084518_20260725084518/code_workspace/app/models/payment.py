"""
Payment domain model with validation
"""
import re
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class PaymentStatus:
    """Payment status enumeration"""
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    
    ALLOWED = [PENDING, VERIFIED, REJECTED]
    
    TRANSITIONS = {
        PENDING: [VERIFIED, REJECTED],
        VERIFIED: [],
        REJECTED: [],
    }


class PaymentMethod:
    """Payment method enumeration"""
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"
    
    ALLOWED = [CREDIT_CARD, BANK_TRANSFER, E_WALLET]


class Payment(BaseModel):
    """Payment entity model"""
    id: UUID = Field(default_factory=uuid4)
    orderRef: UUID
    amount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("99999999.99"))
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    status: str = Field(default=PaymentStatus.PENDING)
    method: str
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent != -2:
            raise ValueError("amount must have exactly 2 decimal places")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in PaymentStatus.ALLOWED:
            raise ValueError(f"status must be one of {PaymentStatus.ALLOWED}")
        return v
    
    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in PaymentMethod.ALLOWED:
            raise ValueError(f"method must be one of {PaymentMethod.ALLOWED}")
        return v
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if status transition is valid"""
        if from_status not in PaymentStatus.TRANSITIONS:
            return False
        return to_status in PaymentStatus.TRANSITIONS[from_status]
