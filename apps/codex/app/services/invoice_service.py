from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.models import InvoiceModel
from app.domain.enums import InvoiceStatus, OrderStatus
from app.domain.mappers import invoice_response, order_response
from app.domain.schemas import InvoiceCreate, InvoiceResponse
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.customer_repository import CustomerRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.services.base_service import CachedService


class InvoiceService(CachedService):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
    ) -> None:
        super().__init__(cache)
        self.session_factory = session_factory

    async def create(self, request: InvoiceCreate) -> InvoiceResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            order = await OrderRepository(session).get_with_items(request.orderRef, for_update=True)
            if order is None:
                raise NotFoundError("Order", request.orderRef)
            if order.status is not OrderStatus.ACCEPTED:
                raise ConflictError(
                    f"Order '{order.id}' is {order.status.value}; invoicing requires ACCEPTED"
                )
            if await InvoiceRepository(session).get_by_order(order.id) is not None:
                raise ConflictError(f"Order '{order.id}' already has an invoice")
            customer = await CustomerRepository(session).get_active(order.customer_id)
            if customer is None:
                raise NotFoundError("Customer", order.customer_id)

            if request.billingInfo is not None:
                if request.billingInfo.name != customer.name:
                    raise BadRequestError("billingInfo.name must match the customer snapshot")
                if (
                    request.billingInfo.address is not None
                    and request.billingInfo.address != customer.address
                ):
                    raise BadRequestError("billingInfo.address must match the customer snapshot")
            if request.totalAmount is not None and request.totalAmount != order.total_amount:
                raise BadRequestError("Supplied totalAmount does not match the order total")

            issue_date = request.issueDate or datetime.now(UTC).date()
            due_date = request.dueDate or issue_date + timedelta(days=7)
            if due_date < issue_date:
                raise BadRequestError("dueDate must be greater than or equal to issueDate")

            invoice = InvoiceModel(
                id=uuid4(),
                order_id=order.id,
                billing_name=customer.name,
                billing_address=customer.address,
                total_amount=order.total_amount,
                issue_date=issue_date,
                due_date=due_date,
                status=InvoiceStatus.ISSUED,
                version=1,
            )
            invoice_repository = InvoiceRepository(session)
            invoice_repository.add(invoice)
            await invoice_repository.flush()
            order.invoice_id = invoice.id
            order.status = OrderStatus.INVOICED
            order.updated_at = datetime.now(UTC)
            order.version += 1
            await session.flush()
            response = invoice_response(invoice)
            updated_order = order_response(order)
            OutboxRepository(session).add(
                aggregate_type="invoice",
                aggregate_id=invoice.id,
                event_type="invoice.issued",
                payload={
                    "invoiceId": str(invoice.id),
                    "orderRef": str(order.id),
                    "totalAmount": format(invoice.total_amount, ".2f"),
                },
            )
        await self._store_cached("invoice", response.id, response, invoice.version)
        await self._store_cached("order", order.id, updated_order, order.version)
        return response

    async def get(self, invoice_id: UUID) -> InvoiceResponse:
        cached = await self._cached("invoice", invoice_id, InvoiceResponse)
        if cached is not None:
            return cached
        async with self.session_factory() as session:
            invoice = await InvoiceRepository(session).get(invoice_id)
            if invoice is None:
                raise NotFoundError("Invoice", invoice_id)
            response = invoice_response(invoice)
        await self._store_cached("invoice", invoice_id, response, invoice.version)
        return response

