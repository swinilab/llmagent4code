import uuid
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class InvoiceStatus(str, Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class BillingInfo(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[\p{L} .'-]+$",
        description="Billing name: snapshot from Customer.name"
    )
    address: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Billing address: snapshot from Customer.address"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be blank or whitespace-only")
        if not re.match(r"^[\p{L} .'-]+$", v, re.UNICODE):
            raise ValueError("name contains invalid characters")
        return v
    
    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("address must not be blank or whitespace-only")
        return v


def validate_date_format(v: str) -> bool:
    """Validate dd/MM/yyyy format and check for real calendar date."""
    if not re.match(r"^\d{2}/\d{2}/\d{4}$", v):
        return False
    try:
        day, month, year = map(int, v.split("/"))
        # This will raise ValueError for invalid dates like 31/02/2026
        datetime(year, month, day)
        return True
    except (ValueError, TypeError):
        return False


class Invoice(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    orderRef: str = Field(
        ...,
        description="Reference to Order.id (UUID), order must be in ACCEPTED status"
    )
    billingInfo: BillingInfo
    totalAmount: str = Field(
        ...,
        pattern=r"^\d{1,8}\.\d{2}$",
        description="Total amount: must equal Order.totalAmount at issue time"
    )
    issueDate: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%d/%m/%Y"),
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Issue date in dd/MM/yyyy format"
    )
    dueDate: str = Field(
        default_factory=lambda: (datetime.utcnow() + timedelta(days=7)).strftime("%d/%m/%Y"),
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Due date in dd/MM/yyyy format, must be >= issueDate"
    )
    status: InvoiceStatus = Field(
        default=InvoiceStatus.ISSUED,
        description="Invoice status following state machine"
    )
    
    @field_validator("orderRef")
    @classmethod
    def validate_order_ref(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError("orderRef must be a valid UUIDv4")
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
    
    @field_validator("issueDate")
    @classmethod
    def validate_issue_date(cls, v: str) -> str:
        if not validate_date_format(v):
            raise ValueError("issueDate must be a valid date in dd/MM/yyyy format (e.g., reject 31/02/2026)")
        return v
    
    @field_validator("dueDate")
    @classmethod
    def validate_due_date(cls, v: str) -> str:
        if not validate_date_format(v):
            raise ValueError("dueDate must be a valid date in dd/MM/yyyy format (e.g., reject 31/02/2026)")
        return v
    
    @model_validator(mode="after")
    def validate_due_date_after_issue_date(self) -> "Invoice":
        if self.issueDate and self.dueDate:
            issue_parts = list(map(int, self.issueDate.split("/")))
            due_parts = list(map(int, self.dueDate.split("/")))
            
            issue_dt = datetime(issue_parts[2], issue_parts[1], issue_parts[0])
            due_dt = datetime(due_parts[2], due_parts[1], due_parts[0])
            
            if due_dt < issue_dt:
                raise ValueError("dueDate must be >= issueDate")
        
        return self
