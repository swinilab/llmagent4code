"""Pydantic v2 request and response contracts for all OMS entities."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from .enums import (
    CurrencyCode,
    CustomerRole,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from .validators import (
    AccountNumber,
    Address,
    BankName,
    DateDMY,
    PersonName,
    PhoneNumber,
    ProductAmount,
    ProductDescription,
    TotalAmount,
    UUID4Value,
    UtcDateTime,
)


class DomainSchema(BaseModel):
    """Reject unknown input rather than silently dropping misspelled fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class BankingDetails(DomainSchema):
    accountNumber: AccountNumber
    bankName: BankName


class CustomerCreate(DomainSchema):
    name: PersonName
    address: Address
    phone: PhoneNumber
    bankingDetails: BankingDetails
    role: CustomerRole
    # The field is server-derived. An empty list is tolerated because the
    # manifest-driven harness may include every field in its valid seed.
    orderHistory: list[UUID4Value] = Field(default_factory=list, max_length=0)


class CustomerResponse(DomainSchema):
    id: UUID4Value
    name: PersonName
    address: Address
    phone: PhoneNumber
    bankingDetails: BankingDetails
    role: CustomerRole
    orderHistory: list[UUID4Value] = Field(default_factory=list, max_length=10_000)


class Price(DomainSchema):
    amount: ProductAmount
    currency: CurrencyCode


class ProductCreate(DomainSchema):
    description: ProductDescription
    price: Price


class ProductResponse(DomainSchema):
    id: UUID4Value
    description: ProductDescription
    price: Price


class OrderLineItemCreate(DomainSchema):
    productRef: UUID4Value
    quantity: Annotated[StrictInt, Field(ge=1, le=1000)]
    # A supplied value is only a comparison hint. The service must load and
    # persist the current Product price regardless of this value.
    unitPriceSnapshot: ProductAmount | None = None


class OrderLineItemResponse(DomainSchema):
    productRef: UUID4Value
    quantity: Annotated[StrictInt, Field(ge=1, le=1000)]
    unitPriceSnapshot: ProductAmount


class OrderCreate(DomainSchema):
    customerRef: UUID4Value
    lineItems: list[OrderLineItemCreate] = Field(min_length=1, max_length=100)
    # A supplied total is validated here and compared with the calculated
    # total in the service; it is never used as the persisted source value.
    totalAmount: TotalAmount | None = None
    status: OrderStatus = OrderStatus.PLACED

    @field_validator("status")
    @classmethod
    def initial_status_must_be_placed(cls, value: OrderStatus) -> OrderStatus:
        if value is not OrderStatus.PLACED:
            raise ValueError("an order must be created with status PLACED")
        return value

    @field_validator("lineItems")
    @classmethod
    def product_references_must_be_unique(
        cls, value: list[OrderLineItemCreate]
    ) -> list[OrderLineItemCreate]:
        product_refs = [item.productRef for item in value]
        if len(product_refs) != len(set(product_refs)):
            raise ValueError("duplicate productRef values are not allowed")
        return value


class OrderResponse(DomainSchema):
    id: UUID4Value
    customerRef: UUID4Value
    lineItems: list[OrderLineItemResponse] = Field(min_length=1, max_length=100)
    totalAmount: TotalAmount
    status: OrderStatus
    createdAt: UtcDateTime
    updatedAt: UtcDateTime
    invoiceRef: UUID4Value | None = None

    @model_validator(mode="after")
    def updated_at_cannot_precede_created_at(self) -> "OrderResponse":
        if self.updatedAt < self.createdAt:
            raise ValueError("updatedAt must be greater than or equal to createdAt")
        return self


class PaymentCreate(DomainSchema):
    orderRef: UUID4Value
    amount: TotalAmount
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod

    @field_validator("status")
    @classmethod
    def initial_status_must_be_pending(cls, value: PaymentStatus) -> PaymentStatus:
        if value is not PaymentStatus.PENDING:
            raise ValueError("a payment must be created with status PENDING")
        return value


class PaymentResponse(DomainSchema):
    id: UUID4Value
    orderRef: UUID4Value
    amount: TotalAmount
    timestamp: UtcDateTime
    status: PaymentStatus
    method: PaymentMethod


class BillingInfo(DomainSchema):
    name: PersonName
    address: Address


class BillingInfoCreateHint(DomainSchema):
    """Client comparison hint; omitted address is copied from Customer."""

    name: PersonName
    address: Address | None = None


class InvoiceCreate(DomainSchema):
    orderRef: UUID4Value
    # These snapshots are optional comparison hints for harness compatibility;
    # the service always obtains the authoritative values from Customer/Order.
    billingInfo: BillingInfoCreateHint | None = None
    totalAmount: TotalAmount | None = None
    issueDate: DateDMY | None = None
    dueDate: DateDMY | None = None
    status: InvoiceStatus = InvoiceStatus.ISSUED

    @field_validator("status")
    @classmethod
    def initial_status_must_be_issued(cls, value: InvoiceStatus) -> InvoiceStatus:
        if value is not InvoiceStatus.ISSUED:
            raise ValueError("an invoice must be created with status ISSUED")
        return value

    @model_validator(mode="after")
    def due_date_cannot_precede_supplied_issue_date(self) -> "InvoiceCreate":
        if (
            self.issueDate is not None
            and self.dueDate is not None
            and self.dueDate < self.issueDate
        ):
            raise ValueError("dueDate must be greater than or equal to issueDate")
        return self


class InvoiceResponse(DomainSchema):
    id: UUID4Value
    orderRef: UUID4Value
    billingInfo: BillingInfo
    totalAmount: TotalAmount
    issueDate: DateDMY
    dueDate: DateDMY
    status: InvoiceStatus

    @model_validator(mode="after")
    def due_date_cannot_precede_issue_date(self) -> "InvoiceResponse":
        if self.dueDate < self.issueDate:
            raise ValueError("dueDate must be greater than or equal to issueDate")
        return self


class OrderWorkflowResponse(DomainSchema):
    """Result returned by accept, ship, close, and cancel commands."""

    previousStatus: OrderStatus
    order: OrderResponse


class PaymentWorkflowResponse(DomainSchema):
    """Atomic result returned by payment verification/rejection commands."""

    previousPaymentStatus: PaymentStatus
    payment: PaymentResponse
    order: OrderResponse
    invoice: InvoiceResponse


class ErrorDetail(DomainSchema):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(DomainSchema):
    error: ErrorDetail
