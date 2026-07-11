"""
Background worker that consumes RabbitMQ queues for deferrable work
(invoice generation, notifications).

This decouples spike-prone work from the request thread (NFR 1.3).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aio_pika

from app.config import settings
from app.infrastructure.logging import setup_logging
from app.infrastructure.queue import get_channel

logger = logging.getLogger(__name__)


async def process_invoice_message(body: dict[str, Any]) -> None:
    """Simulate invoice PDF generation."""
    logger.info("Generating invoice for order %s", body.get("order_id"))
    # In production: call a PDF-generation service, store to S3, etc.
    await asyncio.sleep(0.1)  # simulate work


async def process_notification(body: dict[str, Any]) -> None:
    """Simulate sending a notification (email, SMS, webhook)."""
    logger.info("Sending notification: %s", body.get("type"))
    await asyncio.sleep(0.05)  # simulate work


HANDLERS = {
    settings.invoice_queue_name: process_invoice_message,
    settings.notification_queue_name: process_notification,
}


async def consume_queue(queue_name: str) -> None:
    """Consume messages from *queue_name* forever."""
    channel = await get_channel()
    queue = await channel.declare_queue(queue_name, durable=True)
    handler = HANDLERS[queue_name]

    async with queue.iterator() as qiter:
        async for message in qiter:
            async with message.process(requeue=True):
                try:
                    body = json.loads(message.body.decode())
                    await handler(body)
                except Exception:
                    logger.exception("Failed to process message from %s", queue_name)


async def main() -> None:
    setup_logging()
    logger.info("Starting OMS background worker")

    tasks = [
        asyncio.create_task(consume_queue(settings.invoice_queue_name)),
        asyncio.create_task(consume_queue(settings.notification_queue_name)),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
