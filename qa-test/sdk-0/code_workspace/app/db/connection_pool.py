"""Database connection pool with retry logic.

Implements **NFR 2.2 Fault Detection and Recovery** using tenacity.
"""

import aiosqlite
from tenacity import retry, stop_after_attempt, wait_fixed

DB_PATH = "./data/oms.db"

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def get_connection_with_retry() -> aiosqlite.Connection:
    return await aiosqlite.connect(DB_PATH)
