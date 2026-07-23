"""
RabbitMQ-backed message queue for deferrable work (transactional outbox pattern).

Decoupling mechanism (NFR 1.3):
  - Deferrable work (e.g., invoice generation, shipping notifications) is published
    to RabbitMQ queues.
  - Workers consume asynchronously.
  - Order state changes are written to DB synchronously BEFORE publishing to MQ
    (transactional outbox: we write the event to an outbox table in the same DB
    transaction, then a separate publisher forwards to RabbitMQ).

Queue topology:
  - oms.orders: order lifecycle events
  - oms.invoices: invoice generation
  - oms.shipping: shipping notifications
  - oms.dead-letter: failed messages after retries exhausted
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from oms.config import settings


class MessageQueue:
    """Async RabbitMQ client for publishing and consuming deferrable work."""

    def __init__(self):
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractRobustChannel] = None

    async def connect(self):
        """Establish connection and declare queues."""
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        # Set QoS: prefetch 10 messages per consumer
        await self._channel.set_qos(prefetch_count=10)

        # Declare queues with dead-letter exchange
        queues = {
            "oms.orders": {"durable": True},
            "oms.invoices": {"durable": True},
            "oms.shipping": {"durable": True},
            "oms.dead-letter": {"durable": True},
        }
        for name, kwargs in queues.items():
            await self._channel.declare_queue(name, **kwargs)

    async def disconnect(self):
        """Close connection."""
        if self._connection:
            await self._connection.close()

    async def publish(self, routing_key: str, message: dict):
        """Publish a message to the default exchange with the given routing key."""
        body = json.dumps(message, default=str).encode()
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key=routing_key,
        )

    async def consume(self, queue_name: str, callback: Callable):
        """Register an async consumer for a queue."""
        queue = await self._channel.get_queue(queue_name)
        await queue.consume(callback)


# Singleton
mq = MessageQueue()
