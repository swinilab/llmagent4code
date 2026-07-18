"""
Bounded async queue manager for spike protection (NFR 1.3).

When sudden traffic spikes occur, incoming background tasks are enqueued
in a bounded queue. If the queue is full, new tasks are rejected with
QueueFullError so the HTTP layer can return 503 Service Unavailable
instead of crashing. Multiple worker tasks drain the queue concurrently.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable

from oms.config import settings

logger = logging.getLogger(__name__)


class QueueFullError(Exception):
    """Raised when the bounded queue has reached capacity."""
    pass


class QueueManager:
    """
    Async bounded queue with N worker coroutines.

    Enqueue tasks with ``enqueue``; workers pick them up and execute.
    The queue size is capped at ``settings.queue_max_size``.
    """

    def __init__(
        self,
        max_size: int | None = None,
        worker_count: int | None = None,
    ) -> None:
        self.max_size = max_size or settings.queue_max_size
        self.worker_count = worker_count or settings.queue_worker_count
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_size)
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._processed = 0
        self._failed = 0

    async def start(self) -> None:
        """Start worker coroutines."""
        if self._running:
            return
        # Recreate queue bound to the current event loop
        self._queue = asyncio.Queue(maxsize=self.max_size)
        self._running = True
        for i in range(self.worker_count):
            task = asyncio.create_task(self._worker(i), name=f"queue-worker-{i}")
            self._workers.append(task)
        logger.info("QueueManager started with %d workers (max_size=%d)",
                     self.worker_count, self.max_size)
    async def stop(self) -> None:
        """Stop worker coroutines and drain the queue gracefully."""
        if not self._running:
            return
        self._running = False
        # Signal workers to exit by sending sentinels
        for _ in self._workers:
            try:
                self._queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
        # Wait for workers to finish (bounded wait)
        for w in self._workers:
            try:
                await asyncio.wait_for(w, timeout=5.0)
            except asyncio.TimeoutError:
                w.cancel()
            except asyncio.CancelledError:
                pass
        self._workers.clear()
        logger.info("QueueManager stopped (processed=%d, failed=%d)",
                     self._processed, self._failed)

    async def enqueue(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> None:
        """
        Enqueue a coroutine for background processing.

        Raises QueueFullError if the queue is at capacity.
        """
        if self._queue.full():
            raise QueueFullError(
                f"Queue is full (max_size={self.max_size}) — rejecting task"
            )
        await self._queue.put((func, args, kwargs))

    def try_enqueue(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> bool:
        """
        Non-async enqueue attempt. Returns True on success, False if full.
        """
        try:
            self._queue.put_nowait((func, args, kwargs))
            return True
        except asyncio.QueueFull:
            return False

    async def _worker(self, worker_id: int) -> None:
        """Worker loop that processes tasks from the queue."""
        while self._running:
            try:
                item = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            if item is None:
                break
            func, args, kwargs = item
            try:
                await func(*args, **kwargs)
                self._processed += 1
            except Exception as exc:
                self._failed += 1
                logger.error("Queue worker %d task failed: %s", worker_id, exc)
            finally:
                self._queue.task_done()

    def status(self) -> dict:
        """Return queue metrics for health checks."""
        return {
            "max_size": self.max_size,
            "current_size": self._queue.qsize(),
            "worker_count": self.worker_count,
            "running": self._running,
            "processed": self._processed,
            "failed": self._failed,
        }


# Singleton queue manager used application-wide
queue_manager = QueueManager()