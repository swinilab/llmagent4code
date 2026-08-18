"""
Exception handling for NFR 2.1 - Exception Detection
Provides structured exception detection and handling
"""
from typing import Any, Optional, Dict


class OMSException(Exception):
    """Base exception for OMS system"""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        """
        Initialize OMS exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationException(OMSException):
    """Raised when validation fails (NFR 2.1: System exceptions)"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, status_code=400, details={"field": field})
        self.field = field


class NotFoundException(OMSException):
    """Raised when resource is not found (NFR 2.1: System exceptions)"""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with id {resource_id} not found"
        super().__init__(message, status_code=404, details={
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictException(OMSException):
    """Raised when there's a state conflict (NFR 2.1: System exceptions)"""
    
    def __init__(self, message: str, current_state: Optional[str] = None, expected_state: Optional[str] = None):
        super().__init__(message, status_code=409, details={
            "current_state": current_state,
            "expected_state": expected_state
        })
        self.current_state = current_state
        self.expected_state = expected_state


class TimeoutException(OMSException):
    """Raised on timeout (NFR 2.1: Time out exceptions)"""
    
    def __init__(self, operation: str, timeout_seconds: int):
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        super().__init__(message, status_code=504, details={
            "operation": operation,
            "timeout_seconds": timeout_seconds
        })
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class TransactionException(OMSException):
    """Raised when transaction fails (NFR 2.4: Transactions)"""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None):
        super().__init__(message, status_code=500, details={
            "transaction_id": transaction_id
        })
        self.transaction_id = transaction_id


class RateLimitExceededException(OMSException):
    """Raised when rate limit is exceeded (NFR 1.1)"""
    
    def __init__(self, retry_after_seconds: int = 60):
        message = "Rate limit exceeded"
        super().__init__(message, status_code=429, details={
            "retry_after_seconds": retry_after_seconds
        })
        self.retry_after_seconds = retry_after_seconds


class ServiceUnavailableException(OMSException):
    """Raised when service is unavailable (NFR 2.2: Graceful Degradation)"""
    
    def __init__(self, service_name: str, fallback_available: bool = False):
        message = f"Service '{service_name}' is unavailable"
        if fallback_available:
            message += " - operating in degraded mode"
        super().__init__(message, status_code=503, details={
            "service_name": service_name,
            "fallback_available": fallback_available
        })
        self.service_name = service_name
        self.fallback_available = fallback_available
