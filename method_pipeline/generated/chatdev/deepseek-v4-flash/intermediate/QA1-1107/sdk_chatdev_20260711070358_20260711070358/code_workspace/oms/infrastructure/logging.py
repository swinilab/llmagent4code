"""
Structured logging with JSON output and request correlation IDs.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger
from typing import Optional
from oms.config import settings
from oms.infrastructure.context import correlation_id_var


def setup_logging() -> None:
    """Configure structured JSON logging."""
    logger = logging.getLogger("oms")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    # Attach the CorrelationIdFilter so every log record gets a correlation_id field
    handler.addFilter(CorrelationIdFilter())
    logger.addHandler(handler)

    # Set uvicorn access logs to use JSON format too
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(handler)


def get_logger(name: str = "oms") -> logging.Logger:
    """Get a logger instance with correlation ID support."""
    return logging.getLogger(name)


class CorrelationIdFilter(logging.Filter):
    """Add correlation_id to log records by reading from the request-scoped context variable."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Read from the context variable (set by middleware); fall back to record.extra or empty string
        record.correlation_id = correlation_id_var.get() or getattr(record, "correlation_id", "")
        return True
