import asyncio
from typing import Any

_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

async def enqueue_order_task(task: Any):
    await _queue.put(task)
    return True

def get_queue_depth() -> int:
    return _queue.qsize()
