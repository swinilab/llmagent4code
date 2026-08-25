"""Service layer - business logic, transaction boundaries, workflow orchestration.

Every mutating method opens exactly one ``unit_of_work()``. All writes inside it
commit together or not at all, which is the ACID guarantee NFR 2.4 asks for:
e.g. issuing an invoice writes the invoice row *and* moves the order to INVOICED
*and* stamps order.invoice_ref in a single atomic transaction.

Reads go through the cache -> replica -> primary chain, degrading at each step
rather than failing (NFR 1.2 + 2.2).
"""
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.domain.enums import (
    INVOICE_TRANSITIONS,
    ORDER_TRANSITIONS,
    PAYMENT_TRANSITIONS,
    InvoiceStatus,
    OrderStatus,
    PaymentStatus,
    can_transition,
)
from app.domain.models import (
    CustomerCreate,
    CustomerRead,
    InvoiceCreate,
    InvoiceRead,
    OrderCreate,
    OrderRead,
    PaymentCreate,
    PaymentRead,
    ProductCreate,
    ProductRead,
)
from app.infra.cache import EntityCache
from app.infra.database import read_session, unit_of_work
from app.infra.degradation import feature_registry
from app.repositories.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
)
from app.repositories.schema import Customer, Invoice, Order, OrderLineItem, Payment, Product

logger = logging.getLogger(__name__)


def _guard_transition(machine: dict, current_raw: str, target, entity: str) -> None:
    """Reject an illegal state transition with 409 (Implementation note 2c)."""
    current = type(target)(current_raw)
    if current == target:
        raise ConflictError(f"{entity} is already {target.value}")
    if not can_transition(machine, current, target):
        raise ConflictError(
            f"illegal {entity} transition {current.value} -> {target.value}",
            detail={"from": current.value, "to": target.value},
        )


class BaseService:
    """Shared read-through caching and lookup behaviour for all entity services."""

    entity_name: str

    def __init__(self, cache: EntityCache) -> None:
        self.cache = cache

    async def _cached_read(self, entity_id: uuid.UUID, loader) -> dict:
        """cache -> replica -> primary, degrading at each hop."""
        key = str(entity_id)
        if feature_registry.is_available("cache_acceleration"):
            hit = await self.cache.get(self.entity_name, key)
            if hit is not None:
                return hit

        with read_session() as session:
            payload = loader(session)

        if feature_registry.is_available("cache_acceleration"):
            await self.cache.set(self.entity_name, key, payload)
        return payload

    async def _invalidate(self, entity_id: uuid.UUID) -> None:
        await self.cache.invalidate(self.entity_name, str(entity_id))


# --- Customer -----------------------------------------------------------------


class CustomerService(BaseService):
    entity_name = "customer"

    @staticmethod
    def _to_read(row: Customer, history: list[uuid.UUID]) -> CustomerRead:
        return CustomerRead(
            id=row.id,
            name=row.name,
            address=row.address,
            phone=row.phone,
            bankingDetails={"accountNumber": row.account_number, "bankName": row.bank_name},
            role=row.role,
            orderHistory=history,
        )

    async def create(self, payload: CustomerCreate) -> CustomerRead:
        with unit_of_work() as session:
            row = CustomerRepository(session).add(
                Customer(
                    name=payload.name,
                    address=payload.address,
                    phone=payload.phone,
                    account_number=payload.bankingDetails.accountNumber,
                    bank_name=payload.bankingDetails.bankName,
                    role=payload.role.value,
                )
            )
            result = self._to_read(row, [])
        return result

    async def get(self, customer_id: uuid.UUID) -> CustomerRead:
        def _load(session: Session) -> dict:
            repo = CustomerRepository(session)
            row = repo.get_active(customer_id)
            if row is None:
                raise NotFoundError(f"customer {customer_id} not found")
            history = (
                repo.order_history(customer_id)
                if feature_registry.is_available("order_history_expansion")
                else []
            )
            return self._to_read(row, history).model_dump(mode="json")

        return CustomerRead.model_validate(await self._cached_read(customer_id, _load))


# --- Product ------------------------------------------------------------------


class ProductService(BaseService):
    entity_name = "product"

    @staticmethod
    def _to_read(row: Product) -> ProductRead:
        return ProductRead(
            id=row.id,
            description=row.description,
            price={"amount": f"{Decimal(row.price_amount):.2f}", "currency": row.price_currency},
        )

    async def create(self, payload: ProductCreate) -> ProductRead:
        with unit_of_work() as session:
            row = ProductRepository(session).add(
                Product(
                    description=payload.description,
                    price_amount=payload.price.amount,
                    price_currency=payload.price.currency,
                )
            )
            result = self._to_read(row)
        return result

    async def get(self, product_id: uuid.UUID) -> ProductRead:
        def _load(session: Session) -> dict:
            row = ProductRepository(session).get(product_id)
            if row is None:
                raise NotFoundError(f"product {product_id} not found")
            return self._to_read(row).model_dump(mode="json")

        return ProductRead.model_validate(await self._cached_read(product_id, _load))


# --- Order --------------------------------------------------------------------


class OrderService(BaseService):
    entity_name = "order"

    @staticmethod
    def _to_read(row: Order) -> OrderRead:
        return OrderRead(
            id=row.id,
            customerRef=row.customer_ref,
            lineItems=[
                {
                    "productRef": li.product_ref,
                    "quantity": li.quantity,
                    "unitPriceSnapshot": f"{Decimal(li.unit_price_snapshot):.2f}",
                }
                for li in row.line_items
            ],
            totalAmount=f"{Decimal(row.total_amount):.2f}",
            status=row.status,
            createdAt=row.created_at,
            updatedAt=row.updated_at,
            invoiceRef=row.invoice_ref,
        )

    async def create(self, payload: OrderCreate) -> OrderRead:
        """Workflow step 1 - Customer places order.

        unitPriceSnapshot and totalAmount are computed here from the *current*
        product rows; any client-supplied value was already rejected by the DTO.
        """
        with unit_of_work() as session:
            customers = CustomerRepository(session)
            products = ProductRepository(session)

            if customers.get_active(payload.customerRef) is None:
                raise NotFoundError(f"customer {payload.customerRef} not found")

            wanted = [item.productRef for item in payload.lineItems]
            found = products.get_many(wanted)
            missing = [str(pid) for pid in wanted if pid not in found]
            if missing:
                raise NotFoundError("product(s) not found", detail={"missing": missing})

            currencies = {found[pid].price_currency for pid in wanted}
            if len(currencies) > 1:
                raise ValidationError(
                    "all line items must share one currency", detail={"currencies": sorted(currencies)}
                )

            order = Order(
                customer_ref=payload.customerRef,
                total_amount=Decimal("0.01"),  # replaced below; satisfies NOT NULL
                status=OrderStatus.PLACED.value,
            )
            orders = OrderRepository(session)
            orders.add(order)

            total = Decimal("0.00")
            for item in payload.lineItems:
                snapshot = Decimal(found[item.productRef].price_amount).quantize(Decimal("0.01"))
                total += snapshot * item.quantity
                orders.add_line_item(
                    OrderLineItem(
                        order_id=order.id,
                        product_ref=item.productRef,
                        quantity=item.quantity,
                        unit_price_snapshot=snapshot,
                    )
                )

            if total > Decimal("99999999.99"):
                raise ValidationError(
                    "order totalAmount exceeds the maximum of 99999999.99",
                    detail={"computed": f"{total:.2f}"},
                )

            order.total_amount = total
            session.flush()
            session.refresh(order)
            result = self._to_read(order)
        return result

    async def get(self, order_id: uuid.UUID) -> OrderRead:
        def _load(session: Session) -> dict:
            row = OrderRepository(session).get(order_id)
            if row is None:
                raise NotFoundError(f"order {order_id} not found")
            return self._to_read(row).model_dump(mode="json")

        return OrderRead.model_validate(await self._cached_read(order_id, _load))

    async def transition(self, order_id: uuid.UUID, target: OrderStatus) -> OrderRead:
        """Workflow steps 2, 6, 7 - accept / ship / close, plus cancellation.

        The row is locked FOR UPDATE and the version column is checked on write,
        so two concurrent transitions cannot both succeed (NFR 2.4 isolation).
        """
        with unit_of_work() as session:
            orders = OrderRepository(session)
            order = orders.get_for_update(order_id)
            if order is None:
                raise NotFoundError(f"order {order_id} not found")

            _guard_transition(ORDER_TRANSITIONS, order.status, target, "order")

            # Step 6 precondition: only a payment-verified order may ship.
            if target is OrderStatus.SHIPPED and order.status != OrderStatus.VERIFIED.value:
                raise ConflictError("order must be VERIFIED before shipping")

            order.status = target.value
            order.updated_at = datetime.now(UTC)
            try:
                session.flush()
            except StaleDataError as exc:
                raise ConflictError("order was modified concurrently; retry") from exc
            result = self._to_read(order)

        await self._invalidate(order_id)
        return result


# --- Invoice ------------------------------------------------------------------


class InvoiceService(BaseService):
    entity_name = "invoice"

    @staticmethod
    def _to_read(row: Invoice) -> InvoiceRead:
        return InvoiceRead(
            id=row.id,
            orderRef=row.order_ref,
            billingInfo={"name": row.billing_name, "address": row.billing_address},
            totalAmount=f"{Decimal(row.total_amount):.2f}",
            issueDate=row.issue_date,
            dueDate=row.due_date,
            status=row.status,
        )

    async def create(self, payload: InvoiceCreate) -> InvoiceRead:
        """Workflow step 3 - Accountant creates invoice for an ACCEPTED order.

        Atomic across three writes: insert invoice, set order.invoice_ref, move
        order to INVOICED. A failure at any point leaves none of them applied.
        """
        with unit_of_work() as session:
            orders = OrderRepository(session)
            order = orders.get_for_update(payload.orderRef)
            if order is None:
                raise NotFoundError(f"order {payload.orderRef} not found")
            if order.status != OrderStatus.ACCEPTED.value:
                raise ConflictError(
                    "order must be ACCEPTED before invoicing",
                    detail={"orderStatus": order.status},
                )

            customer = CustomerRepository(session).get_active(order.customer_ref)
            if customer is None:
                raise NotFoundError(f"customer {order.customer_ref} not found")

            issue = payload.issueDate or date.today()
            due = payload.dueDate or (issue + timedelta(days=7))
            if due < issue:
                raise ValidationError("dueDate must not precede issueDate")

            invoice = Invoice(
                order_ref=order.id,
                billing_name=customer.name,      # snapshot, not a live reference
                billing_address=customer.address,
                total_amount=Decimal(order.total_amount).quantize(Decimal("0.01")),
                issue_date=issue,
                due_date=due,
                status=InvoiceStatus.ISSUED.value,
            )
            try:
                InvoiceRepository(session).add(invoice)
            except IntegrityError as exc:
                raise ConflictError("an invoice already exists for this order") from exc

            order.invoice_ref = invoice.id
            order.status = OrderStatus.INVOICED.value
            order.updated_at = datetime.now(UTC)
            session.flush()
            invoice_id = invoice.id
            result = self._to_read(invoice)

        await self._invalidate(invoice_id)
        await OrderService(self.cache)._invalidate(payload.orderRef)
        return result

    async def get(self, invoice_id: uuid.UUID) -> InvoiceRead:
        def _load(session: Session) -> dict:
            row = InvoiceRepository(session).get(invoice_id)
            if row is None:
                raise NotFoundError(f"invoice {invoice_id} not found")
            return self._to_read(row).model_dump(mode="json")

        return InvoiceRead.model_validate(await self._cached_read(invoice_id, _load))

    def mark_overdue(self, today: date | None = None) -> int:
        """Sweep ISSUED invoices past due. Runs in its own transaction."""
        today = today or date.today()
        with unit_of_work() as session:
            repo = InvoiceRepository(session)
            stale = repo.overdue_before(today)
            for inv in stale:
                if can_transition(INVOICE_TRANSITIONS, InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
                    inv.status = InvoiceStatus.OVERDUE.value
            return len(stale)


# --- Payment ------------------------------------------------------------------


class PaymentService(BaseService):
    entity_name = "payment"

    @staticmethod
    def _to_read(row: Payment) -> PaymentRead:
        return PaymentRead(
            id=row.id,
            orderRef=row.order_ref,
            amount=f"{Decimal(row.amount):.2f}",
            timestamp=row.timestamp,
            status=row.status,
            method=row.method,
        )

    async def create(self, payload: PaymentCreate) -> PaymentRead:
        """Workflow step 4 - Customer pays the invoice.

        Requires order.status == INVOICED and an exact amount match against the
        invoice total: no partial and no over-payment in the current scope.
        """
        with unit_of_work() as session:
            orders = OrderRepository(session)
            order = orders.get_for_update(payload.orderRef)
            if order is None:
                raise NotFoundError(f"order {payload.orderRef} not found")
            if order.status != OrderStatus.INVOICED.value:
                raise ConflictError(
                    "order is not in a payable state",
                    detail={"orderStatus": order.status, "required": "INVOICED"},
                )

            invoice = InvoiceRepository(session).get_by_order(order.id)
            if invoice is None:
                raise ConflictError("order has no invoice to pay")

            payments = PaymentRepository(session)
            if payments.has_settled_payment(order.id):
                raise ConflictError("a payment for this order is already pending or verified")

            expected = Decimal(invoice.total_amount).quantize(Decimal("0.01"))
            if payload.amount != expected:
                raise ValidationError(
                    "payment amount must exactly equal the invoice total",
                    detail={"expected": f"{expected:.2f}", "received": f"{payload.amount:.2f}"},
                )

            payment = payments.add(
                Payment(
                    order_ref=order.id,
                    amount=payload.amount,
                    status=PaymentStatus.PENDING.value,
                    method=payload.method.value,
                )
            )

            order.status = OrderStatus.PAID.value
            order.updated_at = datetime.now(UTC)
            invoice.status = InvoiceStatus.PAID.value
            session.flush()
            invoice_id = invoice.id
            result = self._to_read(payment)

        await OrderService(self.cache)._invalidate(payload.orderRef)
        await InvoiceService(self.cache)._invalidate(invoice_id)
        return result

    async def get(self, payment_id: uuid.UUID) -> PaymentRead:
        def _load(session: Session) -> dict:
            row = PaymentRepository(session).get(payment_id)
            if row is None:
                raise NotFoundError(f"payment {payment_id} not found")
            return self._to_read(row).model_dump(mode="json")

        return PaymentRead.model_validate(await self._cached_read(payment_id, _load))

    async def verify(self, payment_id: uuid.UUID, target: PaymentStatus) -> PaymentRead:
        """Workflow step 5 - Accountant verifies (or rejects) the payment.

        VERIFIED advances the order to VERIFIED; REJECTED returns the order to
        INVOICED so the customer can retry. Both happen in one transaction with
        the payment update.
        """
        with unit_of_work() as session:
            payments = PaymentRepository(session)
            payment = payments.get_for_update(payment_id)
            if payment is None:
                raise NotFoundError(f"payment {payment_id} not found")

            _guard_transition(PAYMENT_TRANSITIONS, payment.status, target, "payment")

            order = OrderRepository(session).get_for_update(payment.order_ref)
            if order is None:
                raise NotFoundError(f"order {payment.order_ref} not found")

            payment.status = target.value
            invoice = InvoiceRepository(session).get_by_order(order.id)

            if target is PaymentStatus.VERIFIED:
                order.status = OrderStatus.VERIFIED.value
            else:
                order.status = OrderStatus.INVOICED.value
                if invoice is not None:
                    invoice.status = InvoiceStatus.ISSUED.value
            order.updated_at = datetime.now(UTC)
            session.flush()
            result = self._to_read(payment)

        await self._invalidate(payment_id)
        await OrderService(self.cache)._invalidate(payment.order_ref)
        return result
