"""QueueManager – bounded asyncio.Queue used for background task processing.

Implements **NFR 1.3 Queue Management** and **NFR 2.1 Graceful Degradation** (workers can be paused).
"""

import asyncio
import logging
from typing import Dict, Any

MAX_QUEUE_SIZE = 5000

logger = logging.getLogger("queue_manager")

class QueueManager:
    def __init__(self):
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self._shutdown_event = asyncio.Event()
        self._paused = False

    async def enqueue_order_task(self, task: Dict[str, Any]):
        try:
            await self._queue.put(task)
            logger.info(f"Enqueued task {task['type']} for order {task.get('order_id')}")
        except asyncio.QueueFull:
            logger.error("Queue is full – cannot accept new tasks")
            raise

    async def get_queue_depth(self) -> int:
        return self._queue.qsize()

    async def worker(self):
        while not self._shutdown_event.is_set():
            if self._paused:
                await asyncio.sleep(0.5)
                continue
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                await self._process(task)
            finally:
                self._queue.task_done()

    async def _process(self, task: Dict[str, Any]):
        # Simple dispatcher – in a real system each type would call a service method.
        if task["type"] == "create_invoice":
            from app.services.invoice_service import InvoiceService
            await InvoiceService().create_invoice(task["order_id"])
        elif task["type"] == "process_payment":
            from app.services.payment_service import PaymentService
            await PaymentService().process_payment(task["order_id"])
        else:
            logger.warning(f"Unknown task type: {task['type']}")

    async def shutdown(self):
        self._shutdown_event.set()
        await self._queue.join()

    def pause(self):
        self._paused = True
        logger.info("Queue processing paused for degradation")

    def resume(self):
        self._paused = False
        logger.info("Queue processing resumed")

# Singleton instance used across the app
queue_manager = QueueManager()

# Helper functions for health endpoints
async def get_queue_depth() -> int:
    return await queue_manager.get_queue_depth()
