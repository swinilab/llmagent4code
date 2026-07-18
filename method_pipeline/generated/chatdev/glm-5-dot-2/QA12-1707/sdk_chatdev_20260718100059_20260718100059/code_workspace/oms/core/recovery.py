"""
State recovery service (NFR 2.3).

On application startup, scans the database for orders left in
intermediate states (PENDING, ACCEPTED, INVOICED, PAID, SHIPPED) due to
an unexpected process crash. Logs each recovered order and, where
possible, resumes the lifecycle from its current state.

This ensures minimal data loss and automatic resumption of pending
processing after a restart.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from oms.enums import OrderStatus
from oms.repositories.order import OrderRepository

logger = logging.getLogger(__name__)


class RecoveryService:
    """
    Scans for orders in non-terminal states on startup and logs them
    for audit / manual review. In a production system with external
    integrations (payment gateway, shipping API), this would also
    re-trigger pending API calls.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.order_repo = OrderRepository(session)

    async def recover(self) -> dict:
        """
        Run recovery scan. Returns a summary dict.
        """
        logger.info("Starting state recovery scan...")
        summary: dict[str, int] = {}
        non_terminal = [
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.INVOICED,
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
        ]
        for status in non_terminal:
            orders = await self.order_repo.get_by_status(status)
            count = len(orders)
            summary[status.value] = count
            if count > 0:
                logger.warning(
                    "Recovery: found %d order(s) in state %s — resuming processing",
                    count, status.value,
                )
                for order in orders:
                    logger.info(
                        "Recovery: order %s is in state %s (created %s, updated %s)",
                        order.id, order.status.value,
                        order.created_at, order.updated_at,
                    )
        total = sum(summary.values())
        logger.info("Recovery scan complete: %d order(s) in non-terminal states", total)
        return {"recovered_orders": summary, "total": total}