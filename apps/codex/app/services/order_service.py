from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.models import OrderItemModel, OrderModel
from app.domain.enums import OrderStatus
from app.domain.mappers import order_response
from app.domain.schemas import OrderCreate, OrderResponse, OrderWorkflowResponse
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.product_repository import ProductRepository
from app.services.base_service import CachedService


class OrderService(CachedService):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
    ) -> None:
        super().__init__(cache)
        self.session_factory = session_factory

    async def create(self, request: OrderCreate) -> OrderResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            customer = await CustomerRepository(session).get_active(request.customerRef)
            if customer is None:
                raise NotFoundError("Customer", request.customerRef)

            product_ids = [item.productRef for item in request.lineItems]
            products = await ProductRepository(session).get_many(product_ids)
            for product_id in product_ids:
                if product_id not in products:
                    raise NotFoundError("Product", product_id)

            currencies = {products[product_id].price_currency for product_id in product_ids}
            if len(currencies) != 1:
                raise BadRequestError("All line items in an order must use the same currency")

            total = Decimal("0.00")
            item_models: list[OrderItemModel] = []
            order_id = uuid4()
            for item in request.lineItems:
                product = products[item.productRef]
                snapshot = product.price_amount
                if item.unitPriceSnapshot is not None and item.unitPriceSnapshot != snapshot:
                    raise BadRequestError(
                        f"unitPriceSnapshot for product '{item.productRef}' does not match its current price"
                    )
                total += snapshot * item.quantity
                item_models.append(
                    OrderItemModel(
                        id=uuid4(),
                        order_id=order_id,
                        product_id=item.productRef,
                        quantity=item.quantity,
                        unit_price_snapshot=snapshot,
                    )
                )
            if total < Decimal("0.01") or total > Decimal("99999999.99"):
                raise BadRequestError("Calculated totalAmount must be between 0.01 and 99999999.99")
            if request.totalAmount is not None and request.totalAmount != total:
                raise BadRequestError("Supplied totalAmount does not match the calculated order total")

            now = datetime.now(UTC)
            order = OrderModel(
                id=order_id,
                customer_id=request.customerRef,
                total_amount=total,
                currency=currencies.pop(),
                status=OrderStatus.PLACED,
                created_at=now,
                updated_at=now,
                version=1,
                items=item_models,
            )
            repository = OrderRepository(session)
            repository.add(order)
            await repository.flush()
            response = order_response(order)
            OutboxRepository(session).add(
                aggregate_type="order",
                aggregate_id=order.id,
                event_type="order.placed",
                payload={
                    "orderId": str(order.id),
                    "customerRef": str(order.customer_id),
                    "totalAmount": format(order.total_amount, ".2f"),
                    "currency": order.currency,
                },
            )
        await self._store_cached("order", response.id, response, order.version)
        await self.cache.invalidate("customer", request.customerRef)
        return response

    async def get(self, order_id: UUID) -> OrderResponse:
        cached = await self._cached("order", order_id, OrderResponse)
        if cached is not None:
            return cached
        async with self.session_factory() as session:
            order = await OrderRepository(session).get_with_items(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)
            response = order_response(order)
        await self._store_cached("order", order_id, response, order.version)
        return response

    async def accept(self, order_id: UUID) -> OrderWorkflowResponse:
        return await self._transition(
            order_id,
            allowed={OrderStatus.PLACED},
            target=OrderStatus.ACCEPTED,
            event_type="order.accepted",
        )

    async def ship(self, order_id: UUID) -> OrderWorkflowResponse:
        return await self._transition(
            order_id,
            allowed={OrderStatus.VERIFIED},
            target=OrderStatus.SHIPPED,
            event_type="order.shipped",
        )

    async def close(self, order_id: UUID) -> OrderWorkflowResponse:
        return await self._transition(
            order_id,
            allowed={OrderStatus.SHIPPED},
            target=OrderStatus.CLOSED,
            event_type="order.closed",
        )

    async def cancel(self, order_id: UUID) -> OrderWorkflowResponse:
        return await self._transition(
            order_id,
            allowed={OrderStatus.PLACED, OrderStatus.ACCEPTED},
            target=OrderStatus.CANCELLED,
            event_type="order.cancelled",
        )

    async def _transition(
        self,
        order_id: UUID,
        *,
        allowed: set[OrderStatus],
        target: OrderStatus,
        event_type: str,
    ) -> OrderWorkflowResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            order = await OrderRepository(session).get_with_items(order_id, for_update=True)
            if order is None:
                raise NotFoundError("Order", order_id)
            previous = order.status
            if previous not in allowed:
                expected = ", ".join(sorted(status.value for status in allowed))
                raise ConflictError(
                    f"Order '{order_id}' is {previous.value}; expected one of: {expected}"
                )
            order.status = target
            order.updated_at = datetime.now(UTC)
            order.version += 1
            await session.flush()
            response = order_response(order)
            OutboxRepository(session).add(
                aggregate_type="order",
                aggregate_id=order.id,
                event_type=event_type,
                payload={
                    "orderId": str(order.id),
                    "previousStatus": previous.value,
                    "status": target.value,
                },
            )
        await self._store_cached("order", order_id, response, order.version)
        return OrderWorkflowResponse(previousStatus=previous, order=response)
