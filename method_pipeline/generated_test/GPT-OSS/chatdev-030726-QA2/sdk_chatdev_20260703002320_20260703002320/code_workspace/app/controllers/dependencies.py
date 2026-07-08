"""
FastAPI dependency for DB session.
"""

from typing import Generator
from fastapi import Depends
from app.db import get_db as db_get_db

def get_db() -> Generator:
    """Dependency wrapper that yields a DB session.
    FastAPI will call this for each request.
    """
    # Yield the session from the underlying generator, preserving cleanup.
    yield from db_get_db()
