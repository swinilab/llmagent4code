"""Order repository with optimistic-lock aware update."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update

from app.repositories.base import BaseRepository
from app.repositories.orm_models import OrderModel


class StaleDataError(ValueError):
    """Raised when an optimistic-lock version mismatch occurs."""
    pass


class OrderRepository(BaseRepository[OrderModel]):
    def __init__(self, session):
        super().__init__(OrderModel, session)

    async def update_with_version_check(
        self, order_id: UUID, data: dict[str, Any], expected_version: int
    ) -> Optional[OrderModel]:
        """Update an order with optimistic-lock version check.

        Args:
            order_id: The order UUID.
            data: The data to update.
            expected_version: The version expected (from the read).

        Returns:
            The updated OrderModel.

        Raises:
            StaleDataError: If the version doesn't match (concurrent update).
        """
        data["version"] = expected_version + 1
        stmt = (
            update(OrderModel)
            .where(OrderModel.id == order_id)
            .where(OrderModel.version == expected_version)
            .values(**data)
            .returning(OrderModel)
        )
        result = await self.session.execute(stmt)
        updated = result.scalar_one_or_none()
        if updated is None:
            raise StaleDataError(
                f"Order {order_id} version mismatch: expected {expected_version}"
            )
        await self.session.flush()
        return updated

    async def get_orders_by_customer(self, customer_id: UUID) -> list[OrderModel]:
        """Get all orders for a customer."""
        stmt = select(OrderModel).where(OrderModel.customer_id == customer_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_by_status(self, status: str) -> list[OrderModel]:
        """Get all orders with a given status."""
        stmt = select(OrderModel).where(OrderModel.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
