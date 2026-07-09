"""Structured logging configuration with correlation ID support.

Uses structlog for structured JSON logging with correlation IDs.
"""

import logging
import sys

import structlog

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove default handlers to avoid duplicate output
    root_logger.handlers.clear()

    # Add structlog handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ))
    root_logger.addHandler(handler)
