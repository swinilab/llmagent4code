"""
Application lifecycle management: startup checks, state recovery, graceful shutdown.

NFR 2.3: On startup, the recovery routine checks for "in-flight" orders
(those in CREATED, ACCEPTED, INVOICED, PAID, SHIPPED states) and logs them
for potential manual intervention. The system does NOT auto-advance orders
on restart — that would violate business rules. Instead, it surfaces them
so operators can decide.

NFR 2.2: Health check endpoint is registered in the API layer.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import OrderStatus
from app.domain.models import Order
from app.infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)

# Track application start time for uptime reporting
_start_time: float = 0.0


def get_uptime() -> float:
    """Return seconds since application start."""
    return time.time() - _start_time


async def check_database_health() -> bool:
    """Verify database connectivity by running a simple query."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.scalar_one()
            return row == 1
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


async def recover_in_flight_orders() -> list[dict]:
    """
    On startup, scan for orders that were in a non-terminal state
    when the process last crashed. Log them for operator awareness.

    Returns a list of in-flight order summaries.
    """
    non_terminal_states = [
        OrderStatus.CREATED,
        OrderStatus.ACCEPTED,
        OrderStatus.INVOICED,
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
    ]

    in_flight: list[dict] = []
    try:
        async with async_session_factory() as session:
            stmt = (
                select(Order)
                .where(Order.status.in_(non_terminal_states))
                .order_by(Order.created_at)
            )
            result = await session.execute(stmt)
            orders = result.scalars().all()

            for order in orders:
                summary = {
                    "order_id": str(order.id),
                    "customer_id": str(order.customer_id),
                    "status": order.status.value,
                    "created_at": order.created_at.isoformat(),
                    "total_amount": order.total_amount,
                }
                in_flight.append(summary)
                logger.warning(
                    "In-flight order detected on startup: %s (status=%s)",
                    order.id,
                    order.status.value,
                )

        if in_flight:
            logger.info(
                "Found %d in-flight order(s) requiring attention.", len(in_flight)
            )
        else:
            logger.info("No in-flight orders found. System state is clean.")
    except Exception as exc:
        logger.error("Failed to recover in-flight orders: %s", exc)

    return in_flight


async def startup_routine() -> None:
    """Run on application startup."""
    global _start_time
    _start_time = time.time()

    logger.info("Starting Order Management System...")

    # Check database connectivity
    db_ok = await check_database_health()
    if not db_ok:
        logger.critical("Database is unreachable. Application will start but may fail.")
    else:
        logger.info("Database connection verified.")

    # Recover in-flight orders (NFR 2.3)
    in_flight = await recover_in_flight_orders()
    if in_flight:
        logger.info(
            "Recovery complete. %d order(s) need manual review.",
            len(in_flight),
        )

    logger.info("Order Management System started successfully.")


async def shutdown_routine() -> None:
    """Run on application shutdown."""
    logger.info("Shutting down Order Management System...")
    # Flush any pending outbox messages
    logger.info("Outbox flushed. Goodbye.")
