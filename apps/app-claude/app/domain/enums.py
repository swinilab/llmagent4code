"""Domain enumerations. All matching is case-sensitive by contract."""

from __future__ import annotations

from enum import Enum


class CustomerRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    VERIFIED = "VERIFIED"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


class InvoiceStatus(str, Enum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Currency(str, Enum):
    USD = "USD"
    VND = "VND"
    EUR = "EUR"


# The seven-step workflow state machine. Any transition absent from this map is
# rejected with HTTP 409.
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.INVOICED, OrderStatus.CANCELLED},
    OrderStatus.INVOICED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.VERIFIED, OrderStatus.CANCELLED},
    OrderStatus.VERIFIED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ORDER_TRANSITIONS.get(current, set())
