"""
Async queue manager for order processing with backpressure.
Implements NFR 1.3 (Queue Management) and NFR 2.1 (Graceful Degradation).
Supports priority queuing: essential tasks (checkout, payment) bypass
non-essential tasks (reports, history) under load.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    """Priority levels for queue tasks. Lower number = higher priority."""
    CRITICAL = 0   # Checkout, payment processing
    HIGH = 1       # Order placement, invoice creation
    NORMAL = 2     # Order review, shipping
    LOW = 3        # Reporting, history, search indexing


@dataclass(order=True)
class QueueItem:
    """A queue item with priority sorting."""
    priority: int
    timestamp: float = field(compare=False)
    task_type: str = field(compare=False)
    payload: dict[str, Any] = field(compare=False)
    essential: bool = field(compare=False)


class QueueManager:
    """
    Manages an async work queue with configurable concurrency and priority.
    Drops non-essential tasks when the queue is full (graceful degradation).
    Essential tasks (checkout, payment) always get through.
    """

    def __init__(
        self,
        max_size: int = 0,
        worker_count: int = 0,
        poll_interval: float = 0.0,
    ) -> None:
        self._max_size = max_size or settings.queue_max_size
        self._worker_count = worker_count or settings.queue_worker_count
        self._poll_interval = poll_interval or settings.queue_poll_interval_seconds
        self._queue: asyncio.PriorityQueue[QueueItem] = asyncio.PriorityQueue(
            maxsize=self._max_size
        )
        self._workers: list[asyncio.Task[None]] = []
        self._running = False
        self._dropped_count = 0
        self._processed_count = 0
        self._error_count = 0
        self._peak_queue_size = 0

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def peak_queue_size(self) -> int:
        return self._peak_queue_size

    def _get_priority(self, task_type: str) -> int:
        """Map task type to priority level."""
        priority_map = {
            "process_payment": TaskPriority.CRITICAL,
            "place_order": TaskPriority.HIGH,
            "create_invoice": TaskPriority.HIGH,
            "review_order": TaskPriority.NORMAL,
            "ship_order": TaskPriority.NORMAL,
            "close_order": TaskPriority.NORMAL,
            "send_notification": TaskPriority.LOW,
            "generate_report": TaskPriority.LOW,
        }
        return priority_map.get(task_type, TaskPriority.NORMAL).value

    async def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any],
        essential: bool = False,
    ) -> bool:
        """
        Enqueue a task with priority. If the queue is full and the task
        is non-essential, drop it. Essential tasks always get through.
        Returns True if enqueued, False if dropped.
        """
        priority = self._get_priority(task_type)
        item = QueueItem(
            priority=priority,
            timestamp=time.monotonic(),
            task_type=task_type,
            payload=payload,
            essential=essential,
        )
        try:
            self._queue.put_nowait(item)
            current_size = self._queue.qsize()
            if current_size > self._peak_queue_size:
                self._peak_queue_size = current_size
            return True
        except asyncio.QueueFull:
            if essential:
                # Block until space is available for essential tasks
                await self._queue.put(item)
                current_size = self._queue.qsize()
                if current_size > self._peak_queue_size:
                    self._peak_queue_size = current_size
                return True
            self._dropped_count += 1
            logger.warning(
                "Queue full, dropped non-essential task: %s (dropped=%d, size=%d)",
                task_type,
                self._dropped_count,
                self._queue.qsize(),
            )
            return False

    async def join(self) -> None:
        """Wait until all enqueued tasks have been processed (queue is empty)."""
        await self._queue.join()

    async def start(
        self,
        handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Start worker pool."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i, handler))
            for i in range(self._worker_count)
        ]
        logger.info(
            "QueueManager started with %d workers (max_size=%d)",
            self._worker_count,
            self._max_size,
        )

    async def stop(self) -> None:
        """Gracefully stop all workers."""
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info(
            "QueueManager stopped (processed=%d, dropped=%d, errors=%d, peak=%d)",
            self._processed_count,
            self._dropped_count,
            self._error_count,
            self._peak_queue_size,
        )

    async def _worker_loop(
        self,
        worker_id: int,
        handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        while self._running:
            try:
                item = await asyncio.wait_for(
                    self._queue.get(), timeout=self._poll_interval
                )
                try:
                    await handler(item.task_type, item.payload)
                    self._processed_count += 1
                except Exception:
                    self._error_count += 1
                    logger.exception(
                        "Worker %d failed processing task %s",
                        worker_id,
                        item.task_type,
                    )
                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
