"""
Domain enums shared across all layers.

These enums define the complete lifecycle states for every domain entity
and the role-based access model.
"""
import enum


class Role(str, enum.Enum):
    """User roles served by the OMS."""
    CUSTOMER = "customer"
    ORDER_STAFF = "order_staff"
    ACCOUNTANT = "accountant"


class OrderStatus(str, enum.Enum):
    """
    Full order lifecycle:
    PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
                                  ↘ CANCELLED (terminal, reachable from PENDING/ACCEPTED)
    """
    PENDING = "pending"
    ACCEPTED = "accepted"
    INVOICED = "invoiced"
    PAID = "paid"
    SHIPPED = "shipped"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    """Payment lifecycle."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class PaymentMethod(str, enum.Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"


class InvoiceStatus(str, enum.Enum):
    """Invoice lifecycle."""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"


# ── Allowed transitions (enforced in service layer) ────────────────
ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.INVOICED, OrderStatus.CANCELLED},
    OrderStatus.INVOICED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED},
    OrderStatus.SHIPPED: {OrderStatus.CLOSED},
    OrderStatus.CLOSED: set(),
    OrderStatus.CANCELLED: set(),
}