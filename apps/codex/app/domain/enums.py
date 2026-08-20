"""Closed, case-sensitive value sets used by the OMS domain."""

from enum import Enum


class Role(str, Enum):
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


# Descriptive compatibility alias for callers that prefer an entity-qualified
# name. ``Role`` remains the canonical symbol used by the persistence layer.
CustomerRole = Role


class CurrencyCode(str, Enum):
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
