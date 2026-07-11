"""
Task queue for deferrable work (invoice generation, notifications).
Uses RQ (Redis Queue) to decouple spike-prone work from request threads.
All synchronous RQ calls are offloaded to a thread pool executor to avoid
blocking the async event loop (critical for NFR 1.1).
"""
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional
from redis.asyncio import Redis, ConnectionPool
from rq import Queue as RQQueue
from rq.job import Job
from oms.config import settings

# Dedicated thread pool for offloading synchronous RQ Redis calls.
# 2 workers is sufficient because RQ operations are fast Redis round-trips
# and we only enqueue deferrable (non-critical-path) work.
_rq_executor = ThreadPoolExecutor(max_workers=2)


class TaskQueue:
    """
    Redis-backed task queue for async work.
    Deferrable tasks: invoice generation, email notifications, etc.
    All synchronous RQ calls are offloaded via run_in_executor to keep
    the async event loop responsive.
    """

    def __init__(self, redis_url: str = settings.redis_url):
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._queue: Optional[RQQueue] = None
        self._sync_redis: Any = None
        self._initialized: bool = False
        self._redis_url = redis_url

    async def initialize(self) -> None:
        """Initialize Redis connection and RQ queue."""
        self._pool = ConnectionPool.from_url(
            self._redis_url,
            max_connections=settings.redis_pool_size,
            decode_responses=True,
        )
        self._redis = Redis(connection_pool=self._pool)
        # RQ uses synchronous Redis, so we need a sync client
        import redis as sync_redis
        self._sync_redis = sync_redis.from_url(self._redis_url)
        self._queue = RQQueue(settings.task_queue_name, connection=self._sync_redis)
        self._initialized = True

    async def enqueue(self, task_func: str, *args: Any, **kwargs: Any) -> Optional[str]:
        """
        Enqueue a task for async processing.
        task_func: dotted path to the function (e.g., 'oms.application.tasks.generate_invoice')
        Returns the job ID.

        The synchronous RQ call is offloaded to a thread pool executor so the
        async event loop is not blocked (critical for NFR 1.1 p95 latency targets).
        """
        if self._queue is None:
            return None
        loop = asyncio.get_running_loop()
        job = await loop.run_in_executor(
            _rq_executor,
            lambda: self._queue.enqueue(task_func, *args, **kwargs),
        )
        return job.id

    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Get the status of a job. Offloaded to thread pool to avoid blocking."""
        if self._queue is None:
            return None
        loop = asyncio.get_running_loop()
        job = await loop.run_in_executor(
            _rq_executor,
            lambda: Job.fetch(job_id, connection=self._queue.connection),
        )
        return job.get_status()

    async def close(self) -> None:
        """Close connections."""
        if not self._initialized:
            return
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        if self._sync_redis:
            self._sync_redis.close()


# Singleton instance
task_queue = TaskQueue()


async def get_task_queue() -> TaskQueue:
    """FastAPI dependency to get the task queue."""
    return task_queue
