from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InvoiceModel
from app.repositories.base_repository import BaseRepository


class InvoiceRepository(BaseRepository[InvoiceModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvoiceModel)

    async def get_by_order(self, order_id: UUID, *, for_update: bool = False) -> InvoiceModel | None:
        statement = select(InvoiceModel).where(InvoiceModel.order_id == order_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

