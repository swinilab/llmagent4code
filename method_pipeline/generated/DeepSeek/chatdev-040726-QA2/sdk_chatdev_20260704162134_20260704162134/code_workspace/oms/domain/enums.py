"""
Enumerations for the Order Management System domain.
"""

from enum import Enum


class OrderStatus(str, Enum):
    """Full lifecycle status for an Order."""
    PENDING = "pending"               # Customer placed, awaiting staff review
    ACCEPTED = "accepted"             # Order Staff accepted
    INVOICED = "invoiced"             # Accountant created invoice
    PAID = "paid"                     # Customer paid, payment verified
    SHIPPED = "shipped"               # Order Staff shipped
    COMPLETED = "completed"           # Order Staff closed
    CANCELLED = "cancelled"           # Cancelled at any stage


class PaymentStatus(str, Enum):
    """Status for a Payment."""
    PENDING = "pending"               # Awaiting verification
    VERIFIED = "verified"             # Accountant verified
    FAILED = "failed"                 # Payment failed


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class InvoiceStatus(str, Enum):
    """Status for an Invoice."""
    DRAFT = "draft"                   # Created but not yet sent
    ISSUED = "issued"                 # Sent to customer
    PAID = "paid"                     # Payment received
    OVERDUE = "overdue"               # Past due date
    CANCELLED = "cancelled"           # Cancelled


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


class UserRole(str, Enum):
    """System roles."""
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"
