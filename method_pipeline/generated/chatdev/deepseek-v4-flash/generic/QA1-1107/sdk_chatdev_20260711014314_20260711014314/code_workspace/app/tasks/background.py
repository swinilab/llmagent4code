"""
Background task processor using asyncio queues.
Handles non-blocking operations like notifications, audit logging, and cleanup.
For production, swap this with Celery workers.
"""
import asyncio
import logging
from typing import Any, Callable, Coroutine

from app.config import settings

logger = logging.getLogger(__name__)


class BackgroundTaskProcessor:
    """
    Simple in-process background task processor using asyncio.Queue.
    Processes tasks with configurable concurrency to handle traffic spikes
    without crashing the system (satisfies NFR 1.3 Queue Management).
    """

    def __init__(self, maxsize: int = 1000, num_workers: int = 4):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.num_workers = num_workers
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Start the background worker pool."""
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(i), name=f"bg-worker-{i}")
            for i in range(self.num_workers)
        ]
        logger.info(
            "Started %d background workers (queue maxsize=%d)",
            self.num_workers,
            self.queue.maxsize,
        )

    async def stop(self) -> None:
        """Gracefully stop all workers."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("All background workers stopped")

    async def enqueue(self, task: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> None:
        """
        Enqueue a background task.
        Raises asyncio.QueueFull if the queue is at capacity (backpressure).
        """
        try:
            await asyncio.wait_for(
                self.queue.put((task, args, kwargs)),
                timeout=5.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Background queue full, task dropped (backpressure applied)")
            raise

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop that processes tasks from the queue."""
        while self._running:
            try:
                task, args, kwargs = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )
                try:
                    await task(*args, **kwargs)
                except Exception as e:
                    logger.error("Background task failed: %s", e, exc_info=True)
                finally:
                    self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break


# Singleton instance
_task_processor: BackgroundTaskProcessor | None = None


def get_task_processor() -> BackgroundTaskProcessor:
    """Get or create the singleton background task processor."""
    global _task_processor
    if _task_processor is None:
        _task_processor = BackgroundTaskProcessor(
            maxsize=settings.background_queue_maxsize,
            num_workers=settings.background_workers,
        )
    return _task_processor
