import asyncio
from typing import Dict

class QueueManager:
    def __init__(self, maxsize: int = 1000):
        self._queue = asyncio.Queue(maxsize=maxsize)

    async def enqueue_order_task(self, task: Dict) -> None:
        await self._queue.put(task)

    async def get_queue_depth(self) -> int:
        return self._queue.qsize()

queue_manager = QueueManager()
