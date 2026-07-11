"""
Context variables for request-scoped data (e.g., correlation ID).

Uses Python's contextvars to propagate request-level state across
async boundaries without passing it through every function call.
"""
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
