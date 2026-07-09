"""Domain models for the Order Management System.

These are Pydantic-based domain models used across service and API layers.
They are distinct from SQLAlchemy ORM models (in repositories/) to enforce
separation of concerns.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import (
    Currency,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)


class Customer(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    address: str
    phone: str
    banking_details: str
    order_history: list[UUID] = Field(default_factory=list)
    role: UserRole = UserRole.CUSTOMER
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Product(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    base_price: Decimal = Field(max_digits=12, decimal_places=2)
    currency: Currency = Currency.USD
    stock_available: int = 0
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LineItem(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(max_digits=12, decimal_places=2)
    total_price: Decimal | None = Field(default=None, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def _calculate_total(self) -> "LineItem":
        """Auto-calculate total_price if not explicitly provided.

        Uses Pydantic's @model_validator (mode='after') so that validation
        runs after field parsing but before the model is returned. This avoids
        the ValidationError that would occur with a custom __init__ when
        total_price is absent from input data.
        """
        if self.total_price is None:
            self.total_price = self.unit_price * self.quantity
        return self


class Order(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    total_amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    status: OrderStatus = OrderStatus.CREATED
    invoice_ref: Optional[UUID] = None
    version: int = Field(default=1, ge=1)  # Optimistic-lock version
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class Payment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    currency: Currency = Currency.USD
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod
    idempotency_key: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Invoice(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    customer_name: str
    customer_address: str
    billing_info: str
    subtotal: Decimal = Field(max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    total_amount: Decimal = Field(max_digits=12, decimal_places=2)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
