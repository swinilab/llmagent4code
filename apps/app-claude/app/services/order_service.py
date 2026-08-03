"""Order, Invoice, and Payment services - the seven-step workflow.

`Availability > Prevent Faults > Transactions` (ASR-A4) is applied here, not only
in payment verification: every operation that touches more than one record runs
inside exactly one `session_scope()` with no intermediate commit. Order creation,
Invoice creation, Payment creation, and Payment verification all advance Order
state alongside their own entity, so all four are single atomic units.

Writes are never retried (`retryable=False`): a write whose effect may already
have reached the database must not be blindly re-executed, which is the retry
safety rule ASR-A2 imposes.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.test_hooks import InjectedTransactionFault, should_fault_after_payment_update
from app.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentStatus,
    can_transition,
)
from app.persistence.database import run_with_resilience, session_scope
from app.persistence.models import Invoice, Order, OrderLineItem, Payment
from app.persistence.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
)
from app.schemas.dto import (
    InvoiceCreateRequest,
    InvoiceResponse,
    OrderCreateRequest,
    OrderResponse,
    PaymentCreateRequest,
    PaymentResponse,
    invoice_to_response,
    order_to_response,
    payment_to_response,
)

DEFAULT_PAYMENT_TERM_DAYS = 7


# --------------------------------------------------------------------------
# Step 1 - Customer creates Order
# --------------------------------------------------------------------------


def create_order(payload: OrderCreateRequest) -> OrderResponse:
    def operation() -> OrderResponse:
        with session_scope() as session:
            customer = CustomerRepository(session).get(payload.customerRef)
            if customer is None:
                raise NotFoundError(f"Customer {payload.customerRef} was not found")

            product_ids = [item.productRef for item in payload.lineItems]
            products = ProductRepository(session).get_many(product_ids)
            missing = [pid for pid in product_ids if pid not in products]
            if missing:
                raise NotFoundError(f"Product {missing[0]} was not found")

            order = Order(
                customer_id=customer.id,
                total_amount=Decimal("0.00"),
                status=OrderStatus.PLACED.value,
            )
            repository = OrderRepository(session)
            repository.add(order)

            total = Decimal("0.00")
            for item in payload.lineItems:
                product = products[item.productRef]
                # Snapshot is server-computed from the product price at order
                # time; it is never accepted from the client.
                snapshot = Decimal(product.price_amount)
                total += snapshot * item.quantity
                repository.add_line_item(
                    OrderLineItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=item.quantity,
                        unit_price_snapshot=snapshot,
                    )
                )

            if total > Decimal("99999999.99"):
                raise ValidationError("totalAmount exceeds the maximum of 99999999.99")

            order.total_amount = total
            session.flush()
            session.refresh(order)
            return order_to_response(order)

    return run_with_resilience(operation, operation_name="order.create", retryable=False)


def get_order(order_id: uuid.UUID) -> OrderResponse:
    def operation() -> OrderResponse | None:
        with session_scope() as session:
            order = OrderRepository(session).get(order_id)
            return None if order is None else order_to_response(order)

    result = run_with_resilience(operation, operation_name="order.get")
    if result is None:
        raise NotFoundError(f"Order {order_id} was not found")
    return result


def _transition_order(order_id: uuid.UUID, target: OrderStatus, operation_name: str) -> OrderResponse:
    """Apply a single workflow transition, rejecting illegal ones with 409."""

    def operation() -> OrderResponse:
        with session_scope() as session:
            order = OrderRepository(session).get(order_id)
            if order is None:
                raise NotFoundError(f"Order {order_id} was not found")
            current = OrderStatus(order.status)
            if not can_transition(current, target):
                raise ConflictError(
                    f"Order {order_id} cannot transition from {current.value} to {target.value}"
                )
            order.status = target.value
            session.flush()
            session.refresh(order)
            return order_to_response(order)

    return run_with_resilience(operation, operation_name=operation_name, retryable=False)


# Step 2 - Order Staff accepts Order
def accept_order(order_id: uuid.UUID) -> OrderResponse:
    return _transition_order(order_id, OrderStatus.ACCEPTED, "order.accept")


# Step 6 - Order Staff ships Order
def ship_order(order_id: uuid.UUID) -> OrderResponse:
    return _transition_order(order_id, OrderStatus.SHIPPED, "order.ship")


# Step 7 - Order Staff closes Order
def close_order(order_id: uuid.UUID) -> OrderResponse:
    return _transition_order(order_id, OrderStatus.CLOSED, "order.close")


# --------------------------------------------------------------------------
# Step 3 - Accountant creates Invoice (multi-record: Invoice + Order)
# --------------------------------------------------------------------------


def create_invoice(payload: InvoiceCreateRequest) -> InvoiceResponse:
    def operation() -> InvoiceResponse:
        with session_scope() as session:
            order = OrderRepository(session).get(payload.orderRef)
            if order is None:
                raise NotFoundError(f"Order {payload.orderRef} was not found")

            current = OrderStatus(order.status)
            if current is not OrderStatus.ACCEPTED:
                raise ConflictError(
                    f"Order {payload.orderRef} must be ACCEPTED before invoicing, but is {current.value}"
                )

            customer = CustomerRepository(session).get(order.customer_id)
            if customer is None:
                raise NotFoundError(f"Customer {order.customer_id} was not found")

            issue_date = payload.resolved_issue_date() or date.today()
            due_date = payload.resolved_due_date() or (
                issue_date + timedelta(days=DEFAULT_PAYMENT_TERM_DAYS)
            )
            if due_date < issue_date:
                raise ValidationError("dueDate must not precede issueDate")

            billing = payload.billingInfo
            invoice = Invoice(
                order_id=order.id,
                # Snapshots taken at issue time, not live references.
                billing_name=(billing.name if billing and billing.name else customer.name),
                billing_address=(
                    billing.address if billing and billing.address else customer.address
                ),
                total_amount=Decimal(order.total_amount),
                issue_date=issue_date,
                due_date=due_date,
                status=InvoiceStatus.ISSUED.value,
            )
            InvoiceRepository(session).add(invoice)

            # Both records change inside this one transaction.
            order.status = OrderStatus.INVOICED.value
            order.invoice_id = invoice.id
            session.flush()
            return invoice_to_response(invoice)

    return run_with_resilience(operation, operation_name="invoice.create", retryable=False)


def get_invoice(invoice_id: uuid.UUID) -> InvoiceResponse:
    def operation() -> InvoiceResponse | None:
        with session_scope() as session:
            invoice = InvoiceRepository(session).get(invoice_id)
            return None if invoice is None else invoice_to_response(invoice)

    result = run_with_resilience(operation, operation_name="invoice.get")
    if result is None:
        raise NotFoundError(f"Invoice {invoice_id} was not found")
    return result


# --------------------------------------------------------------------------
# Step 4 - Customer creates Payment (multi-record: Payment + Order)
# --------------------------------------------------------------------------


def create_payment(payload: PaymentCreateRequest) -> PaymentResponse:
    def operation() -> PaymentResponse:
        with session_scope() as session:
            order = OrderRepository(session).get(payload.orderRef)
            if order is None:
                raise NotFoundError(f"Order {payload.orderRef} was not found")

            current = OrderStatus(order.status)
            if current is not OrderStatus.INVOICED:
                raise ConflictError(
                    f"Order {payload.orderRef} must be INVOICED to accept payment, but is {current.value}"
                )

            invoice = InvoiceRepository(session).get_by_order(order.id)
            if invoice is None:
                raise ConflictError(f"Order {payload.orderRef} has no issued invoice")

            amount = Decimal(str(payload.amount))
            if amount != Decimal(invoice.total_amount):
                raise ConflictError(
                    "Payment amount must exactly equal the invoice total; "
                    "partial and over payment are not supported"
                )

            payment = Payment(
                order_id=order.id,
                amount=amount,
                status=PaymentStatus.PENDING.value,
                method=payload.method.value,
            )
            PaymentRepository(session).add(payment)

            # Order advances to PAID while the Payment stays PENDING until an
            # accountant verifies it. Both records change in this one transaction.
            order.status = OrderStatus.PAID.value
            session.flush()
            session.refresh(payment)
            return payment_to_response(payment)

    return run_with_resilience(operation, operation_name="payment.create", retryable=False)


def get_payment(payment_id: uuid.UUID) -> PaymentResponse:
    def operation() -> PaymentResponse | None:
        with session_scope() as session:
            payment = PaymentRepository(session).get(payment_id)
            return None if payment is None else payment_to_response(payment)

    result = run_with_resilience(operation, operation_name="payment.get")
    if result is None:
        raise NotFoundError(f"Payment {payment_id} was not found")
    return result


# --------------------------------------------------------------------------
# Step 5 - Accountant verifies Payment (ASR-A4: three records, one transaction)
# --------------------------------------------------------------------------


def verify_payment(payment_id: uuid.UUID) -> PaymentResponse:
    """Atomically verify a Payment, mark its Invoice PAID, and advance the Order.

    All three updates happen in one transaction with no intermediate commit. The
    `after-payment-update` hook raises between the Payment update and the Invoice
    and Order updates, so the rollback observed by ASR-A4 is the genuine database
    rollback, restoring exactly the end-of-step-4 state
    (Payment PENDING / Invoice ISSUED / Order PAID).
    """

    def operation() -> PaymentResponse:
        with session_scope() as session:
            payment = PaymentRepository(session).get(payment_id)
            if payment is None:
                raise NotFoundError(f"Payment {payment_id} was not found")

            current_payment_status = PaymentStatus(payment.status)
            if current_payment_status is not PaymentStatus.PENDING:
                raise ConflictError(
                    f"Payment {payment_id} must be PENDING to verify, but is {current_payment_status.value}"
                )

            order = OrderRepository(session).get(payment.order_id)
            if order is None:
                raise NotFoundError(f"Order {payment.order_id} was not found")

            current_order_status = OrderStatus(order.status)
            if not can_transition(current_order_status, OrderStatus.VERIFIED):
                raise ConflictError(
                    f"Order {order.id} cannot transition from {current_order_status.value} to VERIFIED"
                )

            invoice = InvoiceRepository(session).get_by_order(order.id)
            if invoice is None:
                raise ConflictError(f"Order {order.id} has no issued invoice")

            # (1) Payment update.
            payment.status = PaymentStatus.VERIFIED.value
            session.flush()

            # Fault point for ASR-A4: raised after the Payment row changed but
            # before the Invoice and Order changes and before commit.
            if should_fault_after_payment_update():
                raise InjectedTransactionFault(
                    "injected fault after payment update, before invoice and order updates"
                )

            # (2) Invoice update and (3) Order update - same transaction.
            invoice.status = InvoiceStatus.PAID.value
            order.status = OrderStatus.VERIFIED.value
            session.flush()
            session.refresh(payment)
            return payment_to_response(payment)

    return run_with_resilience(operation, operation_name="payment.verify", retryable=False)
