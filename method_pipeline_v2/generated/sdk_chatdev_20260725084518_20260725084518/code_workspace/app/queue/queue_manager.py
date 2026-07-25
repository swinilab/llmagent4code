"""
Queue manager for handling async operations and load management
"""
import asyncio
from typing import Callable, Any, Optional
from collections import deque
from datetime import datetime
from app.config.settings import Settings

settings = Settings()


class QueueFullError(Exception):
    """Raised when queue is at capacity"""
    pass


class QueueManager:
    """
    Manages async task queue with bounded size for load management.
    Implements graceful degradation by rejecting new tasks when queue is full.
    """
    
    def __init__(self, max_size: int = None):
        self.max_size = max_size or settings.max_queue_size
        self.queue: deque = deque()
        self.processing = False
        self.worker_count = settings.worker_count
        self.workers: list = []
        self._lock = asyncio.Lock()
        self.processed_count = 0
        self.failed_count = 0
        self.last_processed_at: Optional[datetime] = None
    
    async def enqueue(self, task: Callable, *args, **kwargs) -> bool:
        """
        Add task to queue. Returns False if queue is full (graceful degradation).
        """
        async with self._lock:
            if len(self.queue) >= self.max_size:
                # Graceful degradation: reject new tasks when overloaded
                return False
            
            self.queue.append((task, args, kwargs))
            return True
    
    def size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def is_full(self) -> bool:
        """Check if queue is at capacity"""
        return len(self.queue) >= self.max_size
    
    async def start_workers(self):
        """Start background workers to process queue"""
        self.processing = True
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """Stop all workers"""
        self.processing = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    async def _worker(self, worker_id: int):
        """Worker coroutine to process tasks from queue"""
        while self.processing:
            task_info = None
            async with self._lock:
                if self.queue:
                    task_info = self.queue.popleft()
            
            if task_info:
                task, args, kwargs = task_info
                try:
                    if asyncio.iscoroutinefunction(task):
                        await task(*args, **kwargs)
                    else:
                        task(*args, **kwargs)
                    self.processed_count += 1
                    self.last_processed_at = datetime.utcnow()
                except Exception as e:
                    self.failed_count += 1
            else:
                await asyncio.sleep(0.1)
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        return {
            "queue_size": len(self.queue),
            "max_size": self.max_size,
            "is_full": self.is_full(),
            "processing": self.processing,
            "worker_count": len(self.workers),
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
        }
    
    async def drain(self, timeout_seconds: float = 5.0) -> bool:
        """
        Wait for queue to drain (become empty).
        Returns True if drained within timeout, False otherwise.
        """
        start = datetime.utcnow()
        while self.queue:
            if (datetime.utcnow() - start).total_seconds() > timeout_seconds:
                return False
            await asyncio.sleep(0.1)
        return True


# Global queue instance
_queue_manager: Optional[QueueManager] = None


def get_queue_manager() -> QueueManager:
    """Get or create global queue manager"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
