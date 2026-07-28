"""Readiness check – ensures DB is reachable and queue is operational.

Used by NFR 2.2 and NFR 1.3.
"""

import asyncio
from app.health.liveness import check_db_liveness
from app.queue.queue_manager import get_queue_depth

async def check_readiness() -> bool:
    db_ok = await check_db_liveness()
    if not db_ok:
        return False
    depth = await get_queue_depth()
    # If queue is saturated beyond 80% of max, consider not ready.
    if depth > 0.8 * 5000:
        return False
    return True
