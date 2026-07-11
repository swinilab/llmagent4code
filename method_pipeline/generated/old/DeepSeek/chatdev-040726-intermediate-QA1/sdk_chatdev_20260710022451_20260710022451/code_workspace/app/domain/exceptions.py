"""
Domain exceptions — used by the service layer to signal business-rule violations.
"""


class DomainError(Exception):
    """Base domain exception."""
    detail: str = "A domain rule was violated."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        self.detail = detail or self.detail


class InvalidOrderStateTransition(DomainError):
    """Raised when an order status transition is not allowed."""
    detail = "The requested order status transition is not allowed."

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition from {current} to {target}")


class EntityNotFound(DomainError):
    """Raised when a requested entity does not exist."""
    detail = "The requested entity was not found."

    def __init__(self, entity_type: str, entity_id: int | str) -> None:
        super().__init__(f"{entity_type} with id={entity_id} not found")


class InsufficientStock(DomainError):
    """Raised when a product has insufficient stock."""
    detail = "Insufficient product stock."

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        super().__init__(
            f"Product {product_id}: requested {requested}, available {available}"
        )


class PaymentAlreadyProcessed(DomainError):
    """Raised when attempting to process an already-processed payment."""
    detail = "This payment has already been processed."


class InvoiceAlreadyIssued(DomainError):
    """Raised when attempting to issue an already-issued invoice."""
    detail = "An invoice has already been issued for this order."


class OptimisticLockError(DomainError):
    """Raised when a concurrent modification is detected via version mismatch."""
    detail = "Concurrent modification detected; retry the operation."
