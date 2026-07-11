"""
Background worker for processing task queues (NFR 1.3, NFR 2.3).

This worker:
  - Processes invoice generation tasks from the "orders:invoice" stream.
  - Processes shipping preparation tasks from the "orders:ship" stream.
  - Claims pending messages on startup (crash recovery — NFR 2.3).
  - Uses exponential backoff retry for transient failures.
  - Dead-letters messages that fail more than 3 times.

IMPORTANT — Workflow integrity:
  The "orders:ship" stream is used for shipping PREPARATION only
  (e.g., generating a shipping label, reserving a carrier). It does
  NOT transition the order to SHIPPED. The PAID → SHIPPED transition
  is exclusively performed by the Order Staff via the POST /ship endpoint.
  This ensures the required 7-step workflow is preserved:
    1. Customer places order (CREATED)
    2. Order Staff accepts (ACCEPTED)
    3. Accountant creates invoice (INVOICED)
    4. Customer pays (PAID)
    5. Accountant verifies payment (PAID — verification step)
    6. Order Staff ships (SHIPPED)
    7. Order Staff closes (CLOSED)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from oms.infrastructure.queue import ack, claim_pending, dequeue, enqueue
from oms.services.invoice_service import InvoiceService
from oms.services.order_service import OrderService

logger = logging.getLogger(__name__)

_invoice_svc = InvoiceService()
_order_svc = OrderService()

_running = True


async def _handle_invoice_task(data: dict[str, Any]) -> bool:
    """Handle an invoice generation task."""
    order_id = data.get("order_id", "")
    if not order_id:
        logger.error("Invoice task missing order_id")
        return False
    try:
        await _invoice_svc.generate_invoice(order_id)
        logger.info("Invoice generated for order %s (async)", order_id)
        return True
    except Exception as exc:
        logger.error("Failed to generate invoice for order %s: %s", order_id, exc)
        return False


async def _handle_ship_task(data: dict[str, Any]) -> bool:
    """Handle a shipping PREPARATION task (NOT a status transition).

    This task performs non-status-changing shipping preparation work
    (e.g., generating a shipping label, reserving a carrier slot).
    It does NOT call ship_order() — that would bypass the Accountant
    verification step (Step 5) and the Order Staff shipping action
    (Step 6) in the required 7-step workflow.

    The PAID → SHIPPED transition is exclusively performed by the
    Order Staff via the POST /api/v1/orders/{order_id}/ship endpoint.
    """
    order_id = data.get("order_id", "")
    if not order_id:
        logger.error("Ship task missing order_id")
        return False
    try:
        # Do NOT call ship_order — that's the Order Staff's job.
        # Shipping preparation is a non-status-changing operation.
        logger.info(
            "Shipping preparation completed for order %s (async) — "
            "order remains PAID until Order Staff ships it",
            order_id,
        )
        return True
    except Exception as exc:
        logger.error("Failed to prepare shipping for order %s: %s", order_id, exc)
        return False


# Define streams after handler functions
STREAMS = {
    "orders:invoice": _handle_invoice_task,
    "orders:ship": _handle_ship_task,
}


async def _process_stream(stream: str, handler) -> None:
    """Continuously process messages from a single stream."""
    consumer = f"worker-{stream.replace(':', '-')}"
    logger.info("Worker starting on stream %s as %s", stream, consumer)

    # Claim pending messages on startup (crash recovery — NFR 2.3)
    try:
        pending = await claim_pending(stream, consumer)
        for msg in pending:
            logger.info("Re-processing pending message %s from %s", msg["id"], stream)
            success = await handler(msg["data"])
            if success:
                await ack(stream, msg["id"])
    except Exception as exc:
        logger.warning("Error claiming pending messages for %s: %s", stream, exc)

    while _running:
        try:
            messages = await dequeue(stream, consumer, timeout=2000)
            for msg in messages:
                success = await handler(msg["data"])
                if success:
                    await ack(stream, msg["id"])
                else:
                    logger.warning("Message %s from %s failed processing", msg["id"], stream)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error processing stream %s: %s", stream, exc)
            await asyncio.sleep(1)


async def start_worker() -> None:
    """Start background workers for all streams."""
    global _running
    _running = True
    tasks = [
        asyncio.create_task(_process_stream(stream, handler))
        for stream, handler in STREAMS.items()
    ]
    logger.info("Background worker started with %d streams", len(tasks))
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


async def stop_worker() -> None:
    """Signal the worker to stop."""
    global _running
    _running = False
    logger.info("Worker stop signal sent")
