"""
RabbitMQ-backed deferred-task queue for spike absorption (NFR 1.3).
Deferrable work: invoice generation, notification dispatch, shipping label creation.
"""
from __future__ import annotations

import json
import asyncio
from typing import Any, Callable, Awaitable, Optional

import aio_pika

from oms.infrastructure.config import settings
from oms.infrastructure.metrics import queue_depth

_connection: Optional[aio_pika.RobustConnection] = None
_channel: Optional[aio_pika.RobustChannel] = None


async def get_queue_channel() -> aio_pika.RobustChannel:
    global _connection, _channel
    if _channel is None or _channel.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel()
        await _channel.declare_queue(settings.queue_name, durable=True)
    return _channel


async def enqueue_task(task_type: str, payload: dict) -> None:
    """Publish a deferred task to the broker queue."""
    ch = await get_queue_channel()
    message = aio_pika.Message(
        body=json.dumps({"type": task_type, "payload": payload}).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    await ch.default_exchange.publish(message, routing_key=settings.queue_name)


async def sample_queue_depth() -> int:
    """
    Query the current queue depth (number of messages waiting) from RabbitMQ.
    Returns 0 if the queue cannot be queried (e.g., connection not ready).
    """
    try:
        ch = await get_queue_channel()
        queue = await ch.declare_queue(settings.queue_name, durable=True, passive=True)
        # queue.declaration returns a Queue.DeclareOk with message_count
        depth = queue.declaration.message_count if queue.declaration else 0
        queue_depth.set(depth)
        return depth
    except Exception:
        # If queue is not reachable, report 0 depth to avoid stale metrics
        queue_depth.set(0)
        return 0


async def start_queue_depth_sampler(interval_seconds: float = 5.0) -> asyncio.Task:
    """
    Start a background task that periodically samples the RabbitMQ queue depth
    and updates the Prometheus gauge. This ensures the queue_depth metric is
    always current for NFR monitoring dashboards.
    """
    async def _sample_loop() -> None:
        while True:
            try:
                await sample_queue_depth()
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)

    task = asyncio.create_task(_sample_loop())
    return task


async def start_consumer(
    handler: Callable[[str, dict], Awaitable[None]],
    concurrency: int | None = None,
) -> None:
    """
    Start a consumer pool that processes tasks from the queue.
    *concurrency* defaults to settings.consumer_concurrency (8).
    """
    ch = await get_queue_channel()
    queue = await ch.declare_queue(settings.queue_name, durable=True)
    sem = asyncio.Semaphore(concurrency or settings.consumer_concurrency)

    async def on_message(msg: aio_pika.IncomingMessage) -> None:
        async with sem:
            async with msg.process(ignore_processed=True):
                body = json.loads(msg.body.decode())
                await handler(body["type"], body["payload"])

    await queue.consume(on_message)


async def close_queue() -> None:
    global _connection, _channel
    if _channel and not _channel.is_closed:
        await _channel.close()
    if _connection and not _connection.is_closed:
        await _connection.close()
    _channel = None
    _connection = None
