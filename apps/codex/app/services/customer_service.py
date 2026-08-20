from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import CustomerModel
from app.domain.mappers import customer_response
from app.domain.schemas import CustomerCreate, CustomerResponse
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.customer_repository import CustomerRepository
from app.repositories.outbox_repository import OutboxRepository
from app.core.errors import NotFoundError
from app.services.base_service import CachedService


class CustomerService(CachedService):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
    ) -> None:
        super().__init__(cache)
        self.session_factory = session_factory

    async def create(self, request: CustomerCreate) -> CustomerResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            customer = CustomerModel(
                id=uuid4(),
                name=request.name,
                address=request.address,
                phone=request.phone,
                account_number=request.bankingDetails.accountNumber,
                bank_name=request.bankingDetails.bankName,
                role=request.role,
                version=1,
            )
            repository = CustomerRepository(session)
            repository.add(customer)
            await repository.flush()
            response = customer_response(customer, [])
            OutboxRepository(session).add(
                aggregate_type="customer",
                aggregate_id=customer.id,
                event_type="customer.created",
                payload={"customerId": str(customer.id), "role": customer.role.value},
            )
        await self._store_cached("customer", response.id, response, customer.version)
        return response

    async def get(self, customer_id: UUID) -> CustomerResponse:
        # Order history is server-derived, so it is always refreshed from the
        # canonical relation instead of trusting a potentially stale cache list.
        async with self.session_factory() as session:
            repository = CustomerRepository(session)
            customer = await repository.get_active(customer_id)
            if customer is None:
                raise NotFoundError("Customer", customer_id)
            history = await repository.order_history(customer_id)
            response = customer_response(customer, history)
        await self._store_cached("customer", customer_id, response, customer.version)
        return response

