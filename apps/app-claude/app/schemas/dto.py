"""Request and response DTOs.

Request models forbid extra keys, so any client attempt to supply a computed,
server-generated, immutable, snapshot, or read-only field (`id`, `totalAmount`,
`unitPriceSnapshot`, `status`, `createdAt`, `orderHistory`, ...) is rejected with
HTTP 400 rather than silently ignored.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import (
    Currency,
    CustomerRole,
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.schemas.common import (
    StrictModel,
    format_amount,
    format_calendar_date,
    parse_calendar_date,
    validate_account_number,
    validate_address,
    validate_bank_name,
    validate_description,
    validate_name,
    validate_phone,
    validate_product_amount,
    validate_quantity,
    validate_total_amount,
)


# --------------------------------------------------------------------------
# Error envelope
# --------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["VALIDATION_ERROR"])
    message: str = Field(..., examples=["name must be between 2 and 100 characters"])


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --------------------------------------------------------------------------
# Customer
# --------------------------------------------------------------------------


class BankingDetailsRequest(StrictModel):
    accountNumber: str = Field(..., examples=["123456789012"])
    bankName: str = Field(..., examples=["Bank of Example"])

    @field_validator("accountNumber")
    @classmethod
    def _account_number(cls, value: Any) -> str:
        return validate_account_number(value)

    @field_validator("bankName")
    @classmethod
    def _bank_name(cls, value: Any) -> str:
        return validate_bank_name(value)


class BankingDetailsResponse(BaseModel):
    accountNumber: str
    bankName: str


class CustomerCreateRequest(StrictModel):
    name: str = Field(..., examples=["Ada Lovelace"])
    address: str = Field(..., examples=["12 Analytical Engine Road, London"])
    phone: str = Field(..., examples=["+442071234567"])
    bankingDetails: BankingDetailsRequest
    role: CustomerRole = Field(..., examples=[CustomerRole.CUSTOMER])

    @field_validator("name")
    @classmethod
    def _name(cls, value: Any) -> str:
        return validate_name(value)

    @field_validator("address")
    @classmethod
    def _address(cls, value: Any) -> str:
        return validate_address(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: Any) -> str:
        return validate_phone(value)


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    phone: str
    bankingDetails: BankingDetailsResponse
    role: CustomerRole
    orderHistory: list[uuid.UUID]


# --------------------------------------------------------------------------
# Product
# --------------------------------------------------------------------------


class PriceRequest(StrictModel):
    amount: Any = Field(..., examples=["19.99"])
    currency: Currency = Field(..., examples=[Currency.USD])

    @field_validator("amount")
    @classmethod
    def _amount(cls, value: Any) -> Decimal:
        return validate_product_amount(value)


class PriceResponse(BaseModel):
    amount: str
    currency: Currency


class ProductCreateRequest(StrictModel):
    description: str = Field(..., examples=["Mechanical keyboard, 87 keys"])
    price: PriceRequest

    @field_validator("description")
    @classmethod
    def _description(cls, value: Any) -> str:
        return validate_description(value)


class ProductResponse(BaseModel):
    id: uuid.UUID
    description: str
    price: PriceResponse


class ProductSearchResponse(BaseModel):
    items: list[ProductResponse]
    count: int


# --------------------------------------------------------------------------
# Order
# --------------------------------------------------------------------------


class LineItemRequest(StrictModel):
    productRef: uuid.UUID
    quantity: int = Field(..., examples=[2])

    @field_validator("quantity")
    @classmethod
    def _quantity(cls, value: Any) -> int:
        return validate_quantity(value)


class LineItemResponse(BaseModel):
    productRef: uuid.UUID
    quantity: int
    unitPriceSnapshot: str


class OrderCreateRequest(StrictModel):
    customerRef: uuid.UUID
    lineItems: Annotated[list[LineItemRequest], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def _no_duplicate_products(self) -> "OrderCreateRequest":
        seen: set[uuid.UUID] = set()
        for item in self.lineItems:
            if item.productRef in seen:
                raise ValueError(
                    f"duplicate productRef in lineItems: {item.productRef}"
                )
            seen.add(item.productRef)
        return self


class OrderResponse(BaseModel):
    id: uuid.UUID
    customerRef: uuid.UUID
    lineItems: list[LineItemResponse]
    totalAmount: str
    status: OrderStatus
    createdAt: datetime
    updatedAt: datetime
    invoiceRef: Optional[uuid.UUID]


# --------------------------------------------------------------------------
# Invoice
# --------------------------------------------------------------------------


class BillingInfoRequest(StrictModel):
    """Optional override of the snapshot copied from the Customer."""

    name: Optional[str] = None
    address: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: Any) -> Any:
        return None if value is None else validate_name(value, "billingInfo.name")

    @field_validator("address")
    @classmethod
    def _address(cls, value: Any) -> Any:
        return None if value is None else validate_address(value)


class BillingInfoResponse(BaseModel):
    name: str
    address: str


class InvoiceCreateRequest(StrictModel):
    orderRef: uuid.UUID
    billingInfo: Optional[BillingInfoRequest] = None
    issueDate: Optional[str] = Field(default=None, examples=["01/08/2026"])
    dueDate: Optional[str] = Field(default=None, examples=["08/08/2026"])

    @field_validator("issueDate")
    @classmethod
    def _issue_date(cls, value: Any) -> Any:
        if value is None:
            return None
        parse_calendar_date(value, "issueDate")
        return value

    @field_validator("dueDate")
    @classmethod
    def _due_date(cls, value: Any) -> Any:
        if value is None:
            return None
        parse_calendar_date(value, "dueDate")
        return value

    @model_validator(mode="after")
    def _due_not_before_issue(self) -> "InvoiceCreateRequest":
        if self.issueDate is not None and self.dueDate is not None:
            issue = parse_calendar_date(self.issueDate, "issueDate")
            due = parse_calendar_date(self.dueDate, "dueDate")
            if due < issue:
                raise ValueError("dueDate must not precede issueDate")
        return self

    def resolved_issue_date(self) -> Optional[date]:
        return None if self.issueDate is None else parse_calendar_date(self.issueDate, "issueDate")

    def resolved_due_date(self) -> Optional[date]:
        return None if self.dueDate is None else parse_calendar_date(self.dueDate, "dueDate")


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    orderRef: uuid.UUID
    billingInfo: BillingInfoResponse
    totalAmount: str
    issueDate: str
    dueDate: str
    status: InvoiceStatus


# --------------------------------------------------------------------------
# Payment
# --------------------------------------------------------------------------


class PaymentCreateRequest(StrictModel):
    orderRef: uuid.UUID
    amount: Any = Field(..., examples=["39.98"])
    method: PaymentMethod = Field(..., examples=[PaymentMethod.CREDIT_CARD])

    @field_validator("amount")
    @classmethod
    def _amount(cls, value: Any) -> Decimal:
        return validate_total_amount(value, "amount")


class PaymentResponse(BaseModel):
    id: uuid.UUID
    orderRef: uuid.UUID
    amount: str
    timestamp: datetime
    status: PaymentStatus
    method: PaymentMethod


# --------------------------------------------------------------------------
# Observability
# --------------------------------------------------------------------------


class MetricsResponse(BaseModel):
    cache_hits_total: int
    cache_misses_total: int
    db_product_reads_total: int
    db_product_read_attempts_total: int
    requests_accepted_total: int
    requests_rejected_total: int
    timeouts_total: int
    retry_attempts_total: int
    transaction_rollbacks_total: int


class HealthResponse(BaseModel):
    status: str
    database: Optional[str] = None


# --------------------------------------------------------------------------
# Mapping helpers
# --------------------------------------------------------------------------


def customer_to_response(customer: Any, order_ids: list[uuid.UUID]) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        address=customer.address,
        phone=customer.phone,
        bankingDetails=BankingDetailsResponse(
            accountNumber=customer.bank_account_number,
            bankName=customer.bank_name,
        ),
        role=CustomerRole(customer.role),
        orderHistory=order_ids,
    )


def product_to_response(product: Any) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        description=product.description,
        price=PriceResponse(
            amount=format_amount(product.price_amount),
            currency=Currency(product.price_currency),
        ),
    )


def order_to_response(order: Any) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        customerRef=order.customer_id,
        lineItems=[
            LineItemResponse(
                productRef=item.product_id,
                quantity=item.quantity,
                unitPriceSnapshot=format_amount(item.unit_price_snapshot),
            )
            for item in order.line_items
        ],
        totalAmount=format_amount(order.total_amount),
        status=OrderStatus(order.status),
        createdAt=order.created_at,
        updatedAt=order.updated_at,
        invoiceRef=order.invoice_id,
    )


def invoice_to_response(invoice: Any) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        orderRef=invoice.order_id,
        billingInfo=BillingInfoResponse(
            name=invoice.billing_name,
            address=invoice.billing_address,
        ),
        totalAmount=format_amount(invoice.total_amount),
        issueDate=format_calendar_date(invoice.issue_date),
        dueDate=format_calendar_date(invoice.due_date),
        status=InvoiceStatus(invoice.status),
    )


def payment_to_response(payment: Any) -> PaymentResponse:
    return PaymentResponse(
        id=payment.id,
        orderRef=payment.order_id,
        amount=format_amount(payment.amount),
        timestamp=payment.timestamp,
        status=PaymentStatus(payment.status),
        method=PaymentMethod(payment.method),
    )
