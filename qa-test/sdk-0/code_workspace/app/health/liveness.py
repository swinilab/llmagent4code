"""Liveness check – verifies DB connectivity using retry (tenacity).

Implements **NFR 2.2 Fault Detection and Recovery**.
"""

import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed
from app.db.connection_pool import get_connection_with_retry

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def check_db_liveness() -> bool:
    try:
        conn = await get_connection_with_retry()
        await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
