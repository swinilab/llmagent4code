from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProductModel
from app.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[ProductModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductModel)

    async def get_many(self, product_ids: Iterable[UUID]) -> dict[UUID, ProductModel]:
        ids = list(product_ids)
        if not ids:
            return {}
        products = (await self.session.scalars(select(ProductModel).where(ProductModel.id.in_(ids)))).all()
        return {product.id: product for product in products}

