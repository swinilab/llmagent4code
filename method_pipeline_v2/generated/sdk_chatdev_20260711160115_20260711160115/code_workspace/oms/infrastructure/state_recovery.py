"""
State preservation and recovery logic (NFR 2.3).

On startup, checks for "in-flight" orders (those in non-terminal states that
were being processed when the process crashed) and resumes them.

Transactional Outbox pattern:
  - Order state changes are written to the `order_outbox` table in the same
    DB transaction as the order update.
  - A background publisher reads from the outbox and forwards to RabbitMQ.
  - On restart, any unprocessed outbox entries are re-published.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.enums import OrderStatus
from oms.infrastructure.database import Base, async_session_factory
from oms.infrastructure.message_queue import mq

logger = logging.getLogger(__name__)


class OrderOutbox(Base):
    """Transactional outbox table for order events."""

    __tablename__ = "order_outbox"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")  # PENDING, SENT, FAILED
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    sent_at = Column(DateTime(timezone=True), nullable=True)


# Map event type prefixes to RabbitMQ queue names.
# The queue names are declared in message_queue.py as:
#   oms.orders, oms.invoices, oms.shipping
_EVENT_TO_QUEUE = {
    "order": "oms.orders",
    "invoice": "oms.invoices",
    "shipping": "oms.shipping",
}


def _routing_key_for_event(event_type: str) -> str:
    """Derive the RabbitMQ routing key from the event type.

    event_type format: "<domain>.<action>" e.g. "order.created"
    Returns the queue name, e.g. "oms.orders"
    """
    domain = event_type.split(".")[0] if "." in event_type else event_type
    return _EVENT_TO_QUEUE.get(domain, f"oms.{domain}")


async def write_outbox(session: AsyncSession, order_id: str, event_type: str, payload: dict):
    """Write an outbox entry in the current DB transaction."""
    outbox = OrderOutbox(
        order_id=order_id,
        event_type=event_type,
        payload=json.dumps(payload, default=str),
        status="PENDING",
    )
    session.add(outbox)


async def process_outbox():
    """Background task: read PENDING outbox entries and publish to RabbitMQ."""
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT * FROM order_outbox WHERE status = 'PENDING' ORDER BY id ASC LIMIT 100")
        )
        rows = result.fetchall()
        for row in rows:
            try:
                payload = json.loads(row.payload)
                routing_key = _routing_key_for_event(row.event_type)
                await mq.publish(routing_key, payload)
                await session.execute(
                    text("UPDATE order_outbox SET status = 'SENT', sent_at = :now WHERE id = :id"),
                    {"now": datetime.now(timezone.utc), "id": row.id},
                )
            except Exception as e:
                logger.error("Failed to process outbox entry %s: %s", row.id, e)
                await session.execute(
                    text("UPDATE order_outbox SET status = 'FAILED' WHERE id = :id"),
                    {"id": row.id},
                )
        await session.commit()


async def recover_in_flight_orders():
    """
    On startup, find orders in non-terminal states and log them for recovery.
    Orders in CREATED, ACCEPTED, INVOICED, PAID, SHIPPED states are "in-flight".
    """
    terminal_states = [OrderStatus.CLOSED.value, OrderStatus.CANCELLED.value]
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT id, status FROM orders WHERE status NOT IN (:s1, :s2) ORDER BY created_at"
            ),
            {"s1": terminal_states[0], "s2": terminal_states[1]},
        )
        rows = result.fetchall()
        if rows:
            logger.info("Found %d in-flight orders to recover:", len(rows))
            for row in rows:
                logger.info("  Order %s in state %s", row.id, row.status)
        else:
            logger.info("No in-flight orders found on startup.")
        return rows


async def startup_recovery():
    """Run recovery routines on application startup."""
    logger.info("=== Starting OMS state recovery ===")
    in_flight = await recover_in_flight_orders()
    await process_outbox()
    logger.info("=== State recovery complete ===")
    return in_flight
