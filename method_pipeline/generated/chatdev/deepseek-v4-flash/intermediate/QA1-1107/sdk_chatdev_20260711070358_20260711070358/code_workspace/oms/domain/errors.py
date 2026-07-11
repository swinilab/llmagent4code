"""
Domain-specific error classes for the Order Management System.
"""


class DomainError(Exception):
    """Base class for all domain errors."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class InvalidStateTransitionError(DomainError):
    """Raised when an illegal order state transition is attempted."""
    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            message=f"Cannot transition from {current_status} to {target_status}",
            code="INVALID_STATE_TRANSITION",
        )


class EntityNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="ENTITY_NOT_FOUND",
        )


class BusinessRuleViolationError(DomainError):
    """Raised when a business rule is violated."""
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(message=message, code=code)


class ConcurrencyConflictError(DomainError):
    """Raised when an optimistic lock version conflict occurs."""
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} '{entity_id}' was modified by another transaction",
            code="CONCURRENCY_CONFLICT",
        )
