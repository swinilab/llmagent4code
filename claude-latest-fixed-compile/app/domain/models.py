"""Shared domain models (request DTOs + response models).

These are the contract shared by backend and any client. Field names match the
Field Constraint Table literally, including dot-notation rendered as nested
objects (`bankingDetails.accountNumber`), because the automated BVA/EP harness
mutates request bodies using exactly those names.

`extra="forbid"` is deliberate: server-computed fields (`totalAmount`,
`unitPriceSnapshot`, `id`, `status`) are absent from the Create DTOs, so a
client that tries to set one gets a 400 rather than having it silently ignored
(Implementation note 3).
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.domain.enums import (
    Currency,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Role,
)
from app.domain.validators import (
    AccountNumber,
    Address,
    BankName,
    CurrencyCode,
    DdMmYyyyDate,
    OrderMoney,
    PersonName,
    Phone,
    ProductDescription,
    ProductPrice,
    Quantity,
    Uuid4,
    format_ddmmyyyy,
    format_money,
)

_STRICT = ConfigDict(extra="forbid", str_strip_whitespace=False, populate_by_name=True)


# --- Customer -----------------------------------------------------------------


class BankingDetails(BaseModel):
    model_config = _STRICT
    accountNumber: AccountNumber
    bankName: BankName


class CustomerCreate(BaseModel):
    model_config = _STRICT
    name: PersonName
    address: Address
    phone: Phone
    bankingDetails: BankingDetails
    role: Role


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    address: str
    phone: str
    bankingDetails: BankingDetails
    role: Role
    orderHistory: list[UUID] = Field(default_factory=list)


# --- Product ------------------------------------------------------------------


class Price(BaseModel):
    model_config = _STRICT
    amount: ProductPrice
    currency: CurrencyCode

    @model_validator(mode="after")
    def _currency_supported(self) -> "Price":
        if self.currency not in Currency.__members__:
            raise ValueError(f"currency must be one of {sorted(Currency.__members__)}")
        return self

    @field_serializer("amount")
    def _ser_amount(self, value: Decimal) -> str:
        return format_money(value)


class ProductCreate(BaseModel):
    model_config = _STRICT
    description: ProductDescription
    price: Price


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    description: str
    price: Price


# --- Order --------------------------------------------------------------------


class LineItemCreate(BaseModel):
    """unitPriceSnapshot is intentionally absent - it is server-copied from the
    product at order time and is not client-settable."""

    model_config = _STRICT
    productRef: Uuid4
    quantity: Quantity


class LineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    productRef: UUID
    quantity: int
    unitPriceSnapshot: Decimal

    @field_serializer("unitPriceSnapshot")
    def _ser_snapshot(self, value: Decimal) -> str:
        return format_money(value)


class OrderCreate(BaseModel):
    model_config = _STRICT
    customerRef: Uuid4
    lineItems: list[LineItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _no_duplicate_products(self) -> "OrderCreate":
        seen = {item.productRef for item in self.lineItems}
        if len(seen) != len(self.lineItems):
            raise ValueError("duplicate productRef within the same order is not allowed")
        return self


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customerRef: UUID
    lineItems: list[LineItemRead]
    totalAmount: Decimal
    status: OrderStatus
    createdAt: datetime
    updatedAt: datetime
    invoiceRef: UUID | None = None

    @field_serializer("totalAmount")
    def _ser_total(self, value: Decimal) -> str:
        return format_money(value)


# --- Payment ------------------------------------------------------------------


class PaymentCreate(BaseModel):
    model_config = _STRICT
    orderRef: Uuid4
    amount: OrderMoney
    method: PaymentMethod


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    orderRef: UUID
    amount: Decimal
    timestamp: datetime
    status: PaymentStatus
    method: PaymentMethod

    @field_serializer("amount")
    def _ser_amount(self, value: Decimal) -> str:
        return format_money(value)


# --- Invoice ------------------------------------------------------------------


class BillingInfo(BaseModel):
    model_config = _STRICT
    name: PersonName
    address: Address


class InvoiceCreate(BaseModel):
    """billingInfo and totalAmount are snapshots taken server-side from the
    customer/order at issue time; issueDate/dueDate may be supplied and default
    to today / today+7."""

    model_config = _STRICT
    orderRef: Uuid4
    issueDate: DdMmYyyyDate | None = None
    dueDate: DdMmYyyyDate | None = None

    @model_validator(mode="after")
    def _due_not_before_issue(self) -> "InvoiceCreate":
        if self.issueDate and self.dueDate and self.dueDate < self.issueDate:
            raise ValueError("dueDate must not precede issueDate")
        return self


class InvoiceRead(BaseModel):
    """Dates use the dd/MM/yyyy annotated type on the way *in* as well as out, so
    a serialized response round-trips cleanly back through validation - which is
    exactly what happens when the read path rehydrates a cached entry."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    orderRef: UUID
    billingInfo: BillingInfo
    totalAmount: Decimal
    issueDate: DdMmYyyyDate
    dueDate: DdMmYyyyDate
    status: InvoiceStatus

    @field_serializer("totalAmount")
    def _ser_total(self, value: Decimal) -> str:
        return format_money(value)

    @field_serializer("issueDate", "dueDate")
    def _ser_date(self, value: date) -> str:
        return format_ddmmyyyy(value)


# --- Workflow command DTOs ----------------------------------------------------


class OrderStatusUpdate(BaseModel):
    model_config = _STRICT
    status: OrderStatus


class PaymentVerification(BaseModel):
    model_config = _STRICT
    status: PaymentStatus
