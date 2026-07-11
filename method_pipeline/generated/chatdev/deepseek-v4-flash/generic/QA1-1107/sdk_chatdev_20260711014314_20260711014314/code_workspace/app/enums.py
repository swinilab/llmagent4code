"""
Domain enums for the Order Management System.
"""
from enum import Enum


class OrderStatus(str, Enum):
    """Full lifecycle status for an order."""
    PENDING = "PENDING"
    REVIEW = "REVIEW"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    """Status of a payment transaction."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class InvoiceStatus(str, Enum):
    """Status of an invoice."""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class CustomerRole(str, Enum):
    """Roles in the system."""
    CUSTOMER = "CUSTOMER"
    ORDER_STAFF = "ORDER_STAFF"
    ACCOUNTANT = "ACCOUNTANT"


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    CASH = "CASH"
