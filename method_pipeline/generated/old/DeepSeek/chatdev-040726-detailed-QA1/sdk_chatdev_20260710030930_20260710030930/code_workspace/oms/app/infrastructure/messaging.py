"""RabbitMQ messaging layer for deferrable work (invoice generation, notifications).

Architecture:
  - Producer: services publish work items to a RabbitMQ queue.
  - Consumer: a background worker pool consumes and processes items.
  - Queue: durable, bounded (max-length policy to prevent unbounded growth).

This handles the deferrable portion of NFR 1.3 spike absorption:
  - Synchronous-critical work (checkout, payment) stays in the HTTP path.
  - Deferrable work (invoice generation, email notifications, shipping label
    generation) is queued and processed asynchronously by the consumer pool.
"""

import json
import logging
from typing import Any, Callable, Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from app.config import settings

logger = logging.getLogger(__name__)

_connection: Optional[AbstractRobustConnection] = None
_channel: Optional[aio_pika.Channel] = None
_queue: Optional[aio_pika.Queue] = None


async def init_messaging() -> None:
    """Initialize RabbitMQ connection, channel, and queue."""
    global _connection, _channel, _queue
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    # Set QoS prefetch count to control consumer concurrency
    await _channel.set_qos(prefetch_count=settings.work_queue_prefetch_count)

    # Declare a durable queue with a max-length bound (10,000 messages)
    # to prevent unbounded memory growth (NFR 1.3).
    _queue = await _channel.declare_queue(
        settings.work_queue_name,
        durable=True,
        arguments={
            "x-max-length": 10000,
            "x-overflow": "reject-publish",  # reject new messages when full
        },
    )
    logger.info(
        "RabbitMQ initialized: queue=%s, max_length=10000, prefetch=%d",
        settings.work_queue_name,
        settings.work_queue_prefetch_count,
    )


async def close_messaging() -> None:
    """Close RabbitMQ connection."""
    global _connection, _channel, _queue
    if _connection:
        await _connection.close()
        _connection = None
        _channel = None
        _queue = None


async def publish_work(work_type: str, payload: dict[str, Any]) -> bool:
    """Publish a deferrable work item to the queue.

    Args:
        work_type: Type of work (e.g., "generate_invoice", "send_notification").
        payload: Work payload data.

    Returns:
        True if published, False if queue is full (message rejected).
    """
    if _channel is None:
        logger.warning("Messaging not initialized, work not published")
        return False

    message_body = json.dumps({"type": work_type, "payload": payload}, default=str)
    message = aio_pika.Message(
        body=message_body.encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        content_type="application/json",
    )

    try:
        await _channel.default_exchange.publish(
            message,
            routing_key=settings.work_queue_name,
        )
        return True
    except aio_pika.exceptions.DeliveryError:
        logger.warning("Queue full, work rejected: %s", work_type)
        return False


async def start_consumer(handler: Callable[[str, dict[str, Any]], Any]) -> None:
    """Start consuming work items from the queue.

    Args:
        handler: Async callable receiving (work_type, payload).
    """
    if _queue is None:
        raise RuntimeError("Queue not initialized")

    async def on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(ignore_processed=True):
            try:
                body = json.loads(message.body.decode())
                work_type = body.get("type", "unknown")
                payload = body.get("payload", {})
                await handler(work_type, payload)
                await message.ack()
            except Exception as exc:
                logger.exception("Work processing failed: %s", exc)
                # Reject and requeue for retry (up to max delivery count)
                await message.reject(requeue=True)

    await _queue.consume(on_message)
    logger.info("Consumer started on queue: %s", settings.work_queue_name)
