"""
Invoice domain model with validation
"""
import re
from uuid import UUID, uuid4
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from dateutil import parser as date_parser


class InvoiceStatus:
    """Invoice status enumeration"""
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    
    ALLOWED = [ISSUED, PAID, OVERDUE, CANCELLED]
    
    TRANSITIONS = {
        ISSUED: [PAID, OVERDUE, CANCELLED],
        PAID: [],
        OVERDUE: [PAID, CANCELLED],
        CANCELLED: [],
    }


class BillingInfo(BaseModel):
    """Billing information snapshot"""
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z .'-]+$", v, flags=re.UNICODE):
            raise ValueError("name contains invalid characters")
        if not v.strip():
            raise ValueError("name cannot be blank or whitespace-only")
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("address cannot be blank or whitespace-only")
        return v


class Invoice(BaseModel):
    """Invoice entity model"""
    id: UUID = Field(default_factory=uuid4)
    orderRef: UUID
    billingInfo: BillingInfo
    totalAmount: Decimal = Field(..., ge=Decimal("0.01"), le=Decimal("99999999.99"))
    issueDate: str = Field(...)  # dd/MM/yyyy format
    dueDate: str = Field(...)    # dd/MM/yyyy format
    status: str = Field(default=InvoiceStatus.ISSUED)
    
    @field_validator("totalAmount")
    @classmethod
    def validate_total_amount(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent != -2:
            raise ValueError("totalAmount must have exactly 2 decimal places")
        return v
    
    @field_validator("issueDate")
    @classmethod
    def validate_issue_date(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("issueDate must be in dd/MM/yyyy format")
        # Validate it's a real calendar date
        try:
            day, month, year = map(int, v.split("/"))
            date(year, month, day)
        except (ValueError, TypeError):
            raise ValueError("issueDate is not a valid calendar date")
        return v
    
    @field_validator("dueDate")
    @classmethod
    def validate_due_date(cls, v: str) -> str:
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
            raise ValueError("dueDate must be in dd/MM/yyyy format")
        # Validate it's a real calendar date
        try:
            day, month, year = map(int, v.split("/"))
            date(year, month, day)
        except (ValueError, TypeError):
            raise ValueError("dueDate is not a valid calendar date")
        return v
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in InvoiceStatus.ALLOWED:
            raise ValueError(f"status must be one of {InvoiceStatus.ALLOWED}")
        return v
    
    @model_validator(mode="after")
    def validate_dates(self) -> "Invoice":
        try:
            issue = datetime.strptime(self.issueDate, "%d/%m/%Y").date()
            due = datetime.strptime(self.dueDate, "%d/%m/%Y").date()
            if due < issue:
                raise ValueError("dueDate must be >= issueDate")
        except ValueError as e:
            if "must be >=" in str(e):
                raise
            raise ValueError("Invalid date format")
        return self
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if status transition is valid"""
        if from_status not in InvoiceStatus.TRANSITIONS:
            return False
        return to_status in InvoiceStatus.TRANSITIONS[from_status]
