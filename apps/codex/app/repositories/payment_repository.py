from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentModel
from app.domain.enums import PaymentStatus
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[PaymentModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PaymentModel)

    async def get_pending_by_order(self, order_id: UUID) -> PaymentModel | None:
        statement = select(PaymentModel).where(
            PaymentModel.order_id == order_id,
            PaymentModel.status == PaymentStatus.PENDING,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
