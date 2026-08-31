from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import NotFoundError
from app.db.models import ProductModel
from app.domain.mappers import product_response
from app.domain.schemas import ProductCreate, ProductResponse
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.services.base_service import CachedService


class ProductService(CachedService):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
    ) -> None:
        super().__init__(cache)
        self.session_factory = session_factory

    async def create(self, request: ProductCreate) -> ProductResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            product = ProductModel(
                id=uuid4(),
                description=request.description,
                price_amount=request.price.amount,
                price_currency=request.price.currency.value,
                version=1,
            )
            repository = ProductRepository(session)
            repository.add(product)
            await repository.flush()
            response = product_response(product)
            OutboxRepository(session).add(
                aggregate_type="product",
                aggregate_id=product.id,
                event_type="product.created",
                payload={
                    "productId": str(product.id),
                    "amount": format(product.price_amount, ".2f"),
                    "currency": product.price_currency,
                },
            )
        await self._store_cached("product", response.id, response, product.version)
        return response

    async def get(self, product_id: UUID) -> ProductResponse:
        cached = await self._cached("product", product_id, ProductResponse)
        if cached is not None:
            return cached
        async with self.session_factory() as session:
            product = await ProductRepository(session).get(product_id)
            if product is None:
                raise NotFoundError("Product", product_id)
            response = product_response(product)
        await self._store_cached("product", product_id, response, product.version)
        return response

