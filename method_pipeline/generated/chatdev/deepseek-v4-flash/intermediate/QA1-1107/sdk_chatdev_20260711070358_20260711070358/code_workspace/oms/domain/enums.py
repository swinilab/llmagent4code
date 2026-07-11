"""
Domain enumerations for the Order Management System.
"""
from enum import Enum


class OrderStatus(str, Enum):
    """Full lifecycle of an order with enforced state transitions."""
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

    @classmethod
    def valid_transitions(cls, current: "OrderStatus") -> set["OrderStatus"]:
        """Return the set of valid next states from the current state."""
        transitions = {
            cls.CREATED: {cls.ACCEPTED, cls.CANCELLED},
            cls.ACCEPTED: {cls.INVOICED, cls.CANCELLED},
            cls.INVOICED: {cls.PAID, cls.CANCELLED},
            cls.PAID: {cls.SHIPPED, cls.CANCELLED},
            cls.SHIPPED: {cls.CLOSED},
            cls.CLOSED: set(),
            cls.CANCELLED: set(),
        }
        return transitions.get(current, set())

    def can_transition_to(self, target: "OrderStatus") -> bool:
        return target in self.valid_transitions(self)


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    DIGITAL_WALLET = "DIGITAL_WALLET"
