from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CustomerModel, OrderModel
from app.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[CustomerModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CustomerModel)

    async def get_active(self, customer_id: UUID, *, for_update: bool = False) -> CustomerModel | None:
        statement = select(CustomerModel).where(
            CustomerModel.id == customer_id,
            CustomerModel.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def order_history(self, customer_id: UUID, *, limit: int = 10_000) -> list[UUID]:
        statement = (
            select(OrderModel.id)
            .where(OrderModel.customer_id == customer_id)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(statement)).all())

