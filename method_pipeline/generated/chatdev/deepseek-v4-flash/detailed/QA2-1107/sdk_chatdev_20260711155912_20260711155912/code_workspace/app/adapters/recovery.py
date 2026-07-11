"""
State recovery logic for crash-safe operation (NFR 2.3).

On startup, the system scans for orders in non-terminal states and
provides a summary for operator review. This module also contains the
logic to resume processing of pending orders.

The recovery process is idempotent — running it multiple times is safe.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import OrderStatus
from app.domain.models import Order

logger = logging.getLogger(__name__)


async def get_in_flight_orders(session: AsyncSession) -> list[dict[str, Any]]:
    """
    Retrieve all orders that are in a non-terminal, non-closed state.

    These orders were being processed when the system last crashed and
    may need manual review or automated resumption.
    """
    non_terminal = [
        OrderStatus.CREATED,
        OrderStatus.ACCEPTED,
        OrderStatus.INVOICED,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
    ]

    stmt = (
        select(Order)
        .where(Order.status.in_(non_terminal))
        .order_by(Order.created_at)
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()

    summaries = []
    for order in orders:
        summaries.append({
            "order_id": str(order.id),
            "customer_id": str(order.customer_id),
            "status": order.status.value,
            "total_amount": order.total_amount,
            "created_at": order.created_at.isoformat(),
            "version": order.version,
        })
    return summaries


async def resume_pending_orders(session: AsyncSession) -> list[dict[str, Any]]:
    """
    Attempt to resume processing of orders that were in a pending state.

    Currently, this is a no-op that logs the orders. In a production system,
    this would re-queue messages for downstream processing.

    Returns the list of orders that need attention.
    """
    in_flight = await get_in_flight_orders(session)
    if in_flight:
        logger.info(
            "Found %d in-flight order(s) on recovery. Manual review recommended.",
            len(in_flight),
        )
        for order_summary in in_flight:
            logger.info(
                "  Order %s: status=%s, amount=%.2f",
                order_summary["order_id"],
                order_summary["status"],
                order_summary["total_amount"],
            )
    else:
        logger.info("No in-flight orders found. System state is clean.")

    return in_flight
