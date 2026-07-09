"""
RabbitMQ-backed task queue for deferrable work (invoice generation,
notifications).  This decouples spike-prone work from the request
thread (NFR 1.3).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aio_pika

from app.config import settings

logger = logging.getLogger(__name__)

_connection: Optional[aio_pika.RobustConnection] = None
_channel: Optional[aio_pika.Channel] = None


async def get_connection() -> aio_pika.RobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def get_channel() -> aio_pika.Channel:
    global _channel
    if _channel is None or _channel.is_closed:
        conn = await get_connection()
        _channel = await conn.channel()
        # Prefetch 10 messages per worker
        await _channel.set_qos(prefetch_count=10)
    return _channel


async def declare_queues() -> None:
    """Declare durable queues on startup."""
    ch = await get_channel()
    for qname in (settings.invoice_queue_name, settings.notification_queue_name):
        await ch.declare_queue(qname, durable=True)
    logger.info("RabbitMQ queues declared: %s, %s",
                settings.invoice_queue_name, settings.notification_queue_name)


async def publish_message(queue_name: str, payload: dict[str, Any]) -> None:
    """Publish a JSON message to *queue_name*."""
    ch = await get_channel()
    await ch.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(payload, default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=queue_name,
    )


async def close_queue() -> None:
    global _channel, _connection
    if _channel and not _channel.is_closed:
        await _channel.close()
    if _connection and not _connection.is_closed:
        await _connection.close()
    _channel = None
    _connection = None
