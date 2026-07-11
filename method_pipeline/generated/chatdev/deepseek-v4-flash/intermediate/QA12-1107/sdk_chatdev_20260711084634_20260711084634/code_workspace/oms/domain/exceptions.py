"""
Domain-specific exceptions for the Order Management System.
"""


class DomainError(Exception):
    """Base domain error."""
    pass


class InvalidStateTransitionError(DomainError):
    """Raised when an order state transition is not allowed."""

    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"Cannot transition from {current_status} to {target_status}"
        )


class OrderNotFoundError(DomainError):
    """Raised when an order is not found."""

    def __init__(self, order_id: str):
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")


class ProductNotFoundError(DomainError):
    """Raised when a product is not found."""

    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")


class InsufficientStockError(DomainError):
    """Raised when a product has insufficient stock."""

    def __init__(self, product_id: str, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )


class PaymentFailedError(DomainError):
    """Raised when payment processing fails."""

    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        self.reason = reason
        super().__init__(f"Payment {payment_id} failed: {reason}")


class PaymentNotFoundError(DomainError):
    """Raised when a payment is not found."""

    def __init__(self, payment_id: str):
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} not found")


class InvoiceNotFoundError(DomainError):
    """Raised when an invoice is not found."""

    def __init__(self, invoice_id: str):
        self.invoice_id = invoice_id
        super().__init__(f"Invoice {invoice_id} not found")


class CustomerNotFoundError(DomainError):
    """Raised when a customer is not found."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Customer {customer_id} not found")


class ConcurrencyConflictError(DomainError):
    """Raised when an optimistic lock conflict occurs."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Concurrency conflict on {entity_type} {entity_id}: "
            f"entity was modified by another transaction"
        )


class InvalidPaymentMethodError(DomainError):
    """Raised when an invalid payment method is provided."""

    def __init__(self, method: str):
        self.method = method
        super().__init__(f"Invalid payment method: {method}")


class PaymentAmountMismatchError(DomainError):
    """Raised when the payment amount does not match the order total."""

    def __init__(self, order_id: str, expected: str, got: str):
        self.order_id = order_id
        self.expected = expected
        self.got = got
        super().__init__(
            f"Payment amount mismatch for order {order_id}: "
            f"expected {expected}, got {got}"
        )
