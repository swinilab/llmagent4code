"""
Logging configuration for the Order Management System.

Structured JSON logging is used for production observability.
In development, human-readable output is used.
"""
from __future__ import annotations

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure the root logger."""
    level = logging.DEBUG if debug else logging.INFO
    fmt = (
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        if debug
        else "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
