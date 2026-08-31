from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.models import PaymentModel
from app.domain.enums import InvoiceStatus, OrderStatus, PaymentStatus
from app.domain.mappers import invoice_response, order_response, payment_response
from app.domain.schemas import PaymentCreate, PaymentResponse, PaymentWorkflowResponse
from app.infrastructure.cache import EntityCache
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.payment_repository import PaymentRepository
from app.services.base_service import CachedService


class PaymentService(CachedService):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache: EntityCache,
    ) -> None:
        super().__init__(cache)
        self.session_factory = session_factory

    async def create(self, request: PaymentCreate) -> PaymentResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            order = await OrderRepository(session).get_with_items(request.orderRef, for_update=True)
            if order is None:
                raise NotFoundError("Order", request.orderRef)
            if order.status is not OrderStatus.INVOICED:
                raise ConflictError(
                    f"Order '{order.id}' is {order.status.value}; payment requires INVOICED"
                )
            invoice = await InvoiceRepository(session).get_by_order(order.id, for_update=True)
            if invoice is None:
                raise ConflictError(f"Order '{order.id}' has no payable invoice")
            if invoice.status not in {InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE}:
                raise ConflictError(f"Invoice '{invoice.id}' is not payable")
            if request.amount != invoice.total_amount:
                raise BadRequestError("Payment amount must exactly equal the invoice totalAmount")

            now = datetime.now(UTC)
            payment = PaymentModel(
                id=uuid4(),
                order_id=order.id,
                amount=invoice.total_amount,
                timestamp=now,
                status=PaymentStatus.PENDING,
                method=request.method,
                version=1,
            )
            payment_repository = PaymentRepository(session)
            payment_repository.add(payment)
            order.status = OrderStatus.PAID
            order.updated_at = now
            order.version += 1
            await payment_repository.flush()
            response = payment_response(payment)
            updated_order = order_response(order)
            OutboxRepository(session).add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type="payment.submitted",
                payload={
                    "paymentId": str(payment.id),
                    "orderRef": str(order.id),
                    "amount": format(payment.amount, ".2f"),
                    "method": payment.method.value,
                },
            )
        await self._store_cached("payment", response.id, response, payment.version)
        await self._store_cached("order", order.id, updated_order, order.version)
        return response

    async def get(self, payment_id: UUID) -> PaymentResponse:
        cached = await self._cached("payment", payment_id, PaymentResponse)
        if cached is not None:
            return cached
        async with self.session_factory() as session:
            payment = await PaymentRepository(session).get(payment_id)
            if payment is None:
                raise NotFoundError("Payment", payment_id)
            response = payment_response(payment)
        await self._store_cached("payment", payment_id, response, payment.version)
        return response

    async def verify(self, payment_id: UUID) -> PaymentWorkflowResponse:
        return await self._review(payment_id, verify=True)

    async def reject(self, payment_id: UUID) -> PaymentWorkflowResponse:
        return await self._review(payment_id, verify=False)

    async def _review(self, payment_id: UUID, *, verify: bool) -> PaymentWorkflowResponse:
        unit_of_work = SqlAlchemyUnitOfWork(self.session_factory)
        async with unit_of_work.transaction() as session:
            payment = await PaymentRepository(session).get(payment_id, for_update=True)
            if payment is None:
                raise NotFoundError("Payment", payment_id)
            if payment.status is not PaymentStatus.PENDING:
                raise ConflictError(
                    f"Payment '{payment.id}' is {payment.status.value}; review requires PENDING"
                )
            order = await OrderRepository(session).get_with_items(payment.order_id, for_update=True)
            if order is None:
                raise NotFoundError("Order", payment.order_id)
            if order.status is not OrderStatus.PAID:
                raise ConflictError(
                    f"Order '{order.id}' is {order.status.value}; review requires PAID"
                )
            invoice = await InvoiceRepository(session).get_by_order(order.id, for_update=True)
            if invoice is None:
                raise ConflictError(f"Order '{order.id}' has no invoice")

            previous_payment_status = payment.status
            now = datetime.now(UTC)
            if verify:
                payment.status = PaymentStatus.VERIFIED
                order.status = OrderStatus.VERIFIED
                invoice.status = InvoiceStatus.PAID
                event_type = "payment.verified"
            else:
                payment.status = PaymentStatus.REJECTED
                order.status = OrderStatus.INVOICED
                event_type = "payment.rejected"
            payment.version += 1
            order.version += 1
            order.updated_at = now
            invoice.version += 1
            await session.flush()

            payment_result = payment_response(payment)
            order_result = order_response(order)
            invoice_result = invoice_response(invoice)
            OutboxRepository(session).add(
                aggregate_type="payment",
                aggregate_id=payment.id,
                event_type=event_type,
                payload={
                    "paymentId": str(payment.id),
                    "orderRef": str(order.id),
                    "status": payment.status.value,
                },
            )
        await self._store_cached("payment", payment.id, payment_result, payment.version)
        await self._store_cached("order", order.id, order_result, order.version)
        await self._store_cached("invoice", invoice.id, invoice_result, invoice.version)
        return PaymentWorkflowResponse(
            previousPaymentStatus=previous_payment_status,
            payment=payment_result,
            order=order_result,
            invoice=invoice_result,
        )
