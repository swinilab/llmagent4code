"""Domain enums and the workflow state machines.

Allowed values mirror the Field Constraint Table exactly; validation is
case-sensitive exact match (Implementation note 1).
"""
from enum import Enum


class Role(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class Currency(str, Enum):
    USD = "USD"
    VND = "VND"
    EUR = "EUR"


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


# --- State machines (single source of truth for legal transitions) ------------
# Behavior Workflow steps 1-7 map onto ORDER_TRANSITIONS in order.

ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PLACED: frozenset({OrderStatus.ACCEPTED, OrderStatus.CANCELLED}),
    OrderStatus.ACCEPTED: frozenset({OrderStatus.INVOICED, OrderStatus.CANCELLED}),
    OrderStatus.INVOICED: frozenset({OrderStatus.PAID, OrderStatus.CANCELLED}),
    OrderStatus.PAID: frozenset({OrderStatus.VERIFIED, OrderStatus.CANCELLED}),
    OrderStatus.VERIFIED: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.CLOSED}),
    OrderStatus.CLOSED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

PAYMENT_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset({PaymentStatus.VERIFIED, PaymentStatus.REJECTED}),
    PaymentStatus.VERIFIED: frozenset(),
    PaymentStatus.REJECTED: frozenset(),
}

INVOICE_TRANSITIONS: dict[InvoiceStatus, frozenset[InvoiceStatus]] = {
    InvoiceStatus.ISSUED: frozenset(
        {InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED}
    ),
    InvoiceStatus.OVERDUE: frozenset({InvoiceStatus.PAID, InvoiceStatus.CANCELLED}),
    InvoiceStatus.PAID: frozenset(),
    InvoiceStatus.CANCELLED: frozenset(),
}


def can_transition(machine: dict, current, target) -> bool:
    return target in machine.get(current, frozenset())
