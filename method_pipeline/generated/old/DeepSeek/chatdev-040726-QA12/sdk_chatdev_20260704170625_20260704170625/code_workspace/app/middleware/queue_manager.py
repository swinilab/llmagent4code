"""Queue Manager — handles sudden traffic spikes (NFR 1.3).

Uses an in-process asyncio queue with configurable max size.
When the queue is full, new requests are rejected with 429 so the system
does not crash. A background worker drains the queue in batches.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Awaitable

from app.config import settings

logger = logging.getLogger("oms.queue")

_logger_initialized = False


def _ensure_logger() -> None:
    global _logger_initialized
    if not _logger_initialized:
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )
        _logger_initialized = True


@dataclass
class QueueTask:
    """A unit of work submitted to the queue."""

    name: str
    payload: dict[str, Any]
    callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None


class QueueManager:
    """Bounded async queue with a background drain worker."""

    def __init__(self) -> None:
        _ensure_logger()
        self._queue: asyncio.Queue[QueueTask] = asyncio.Queue(
            maxsize=settings.QUEUE_MAX_SIZE
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def size(self) -> int:
        return self._queue.qsize()

    async def submit(self, task: QueueTask) -> bool:
        """Submit a task. Returns False if queue is full (will not crash)."""
        try:
            self._queue.put_nowait(task)
            logger.info("Queued task: %s (queue size=%d)", task.name, self.size)
            return True
        except asyncio.QueueFull:
            logger.warning("Queue full (>%d). Rejecting task: %s", settings.QUEUE_MAX_SIZE, task.name)
            return False

    async def _drain_worker(self) -> None:
        """Background worker that drains the queue in batches."""
        while self._running:
            batch: list[QueueTask] = []
            try:
                # Wait for at least one item
                task = await asyncio.wait_for(
                    self._queue.get(), timeout=settings.QUEUE_POLL_SECONDS
                )
                batch.append(task)
            except asyncio.TimeoutError:
                continue

            # Collect up to BATCH_SIZE items
            while len(batch) < settings.QUEUE_BATCH_SIZE:
                try:
                    task = self._queue.get_nowait()
                    batch.append(task)
                except asyncio.QueueEmpty:
                    break

            # Process batch
            logger.info("Processing batch of %d task(s)", len(batch))
            for t in batch:
                try:
                    if t.callback:
                        await t.callback(t.payload)
                    self._queue.task_done()
                except Exception:
                    logger.exception("Failed to process task: %s", t.name)
                    self._queue.task_done()

    def start(self) -> None:
        """Start the background drain worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._drain_worker())
        logger.info("Queue worker started (max=%d, batch=%d)", settings.QUEUE_MAX_SIZE, settings.QUEUE_BATCH_SIZE)

    async def stop(self) -> None:
        """Gracefully stop the worker and drain remaining items."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        # Drain remaining
        remaining = self._queue.qsize()
        if remaining:
            logger.info("Draining %d remaining queue items...", remaining)
        await self._queue.join()
        logger.info("Queue worker stopped")


# Singleton instance
queue_manager = QueueManager()