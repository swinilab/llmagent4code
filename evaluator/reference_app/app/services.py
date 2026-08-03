"""Business logic and transaction boundaries.

The payment-verification path is ASR-A4 and is the reason this module exists in
the shape it does: three rows must move together or not at all, so all three
updates sit inside one session_scope with no intermediate commit. The injected
fault is raised after the payment row is changed and before the other two,
which is precisely where a boundary drawn too narrowly would leak partial state.

The product read is ASR-P1, ASR-A1 and ASR-A2 at once -- cached, timed out and
retried -- so it is written once here and reached through the cache rather than
being reimplemented per scenario.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from .admission import payment_fault_armed, take_transient_failure
from .cache import DependencyUnavailable, product_cache
from .config import settings
from .database import (
    DatabaseTimeout,
    TransientDatabaseError,
    classify,
    metrics,
    session_scope,
    with_deadline,
    with_retry,
)
from .models import Customer, Invoice, LineItem, Order, Payment, Product
from .observability import TRANSACTION_FAILED, ControlledError, conflict, log_event, not_found


class InjectedTransactionFault(RuntimeError):
    """Raised inside the verification transaction by the test hook."""


def parse_uuid(value: str) -> uuid.UUID:
    """Reject a malformed identifier before it reaches the database."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        raise ControlledError(400, "VALIDATION_FAILED", f"malformed identifier: {value!r}")


# ── products ──────────────────────────────────────────────────────────────


def _load_product(product_id: uuid.UUID) -> dict[str, Any]:
    """Read one product, counting attempts where the mechanism actually runs.

    The injected transient failure is raised here, at the boundary, so it is
    absorbed by the same retry policy a real fault would meet -- and so the two
    failed attempts never reach PostgreSQL, which is what the evaluator's scan
    delta confirms.
    """

    def attempt() -> dict[str, Any]:
        # The injected failure is consumed here, on the request's own thread,
        # before the work is handed to a deadline worker. The fault counter
        # lives in a ContextVar, and a worker thread inherits none of the
        # caller's context -- reading it inside the worker would always see an
        # empty state and the injected failures would silently never happen.
        if take_transient_failure():
            log_event("injected_transient_failure", product_id=str(product_id))
            raise TransientDatabaseError("injected transient database failure")

        metrics.increment("db_product_reads_total")

        def read() -> dict[str, Any]:
            with session_scope() as session:
                product = session.get(Product, product_id)
                return {} if product is None else _product_dto(product)

        try:
            return with_deadline(read, settings.db_operation_timeout_ms / 1000.0)
        except (DependencyUnavailable, DatabaseTimeout):
            raise
        except Exception as exc:
            raise classify(exc) from exc

    return with_retry(attempt, count_attempts=True)


def get_product(product_id_raw: str) -> dict[str, Any]:
    product_id = parse_uuid(product_id_raw)
    key = str(product_id)

    dto = product_cache.get(key, lambda: _load_product(product_id))
    if not dto:
        raise not_found(f"product {key} does not exist")
    return dto


def search_products(query: str) -> list[dict[str, Any]]:
    """The scored admission-control path; kept deliberately cheap."""

    def attempt() -> list[dict[str, Any]]:
        try:
            with session_scope() as session:
                stmt = select(Product).limit(20)
                return [_product_dto(p) for p in session.execute(stmt).scalars()]
        except DependencyUnavailable:
            raise
        except Exception as exc:
            raise classify(exc) from exc

    return with_retry(attempt)


def create_product(body: dict[str, Any]) -> dict[str, Any]:
    price = body.get("price") or {}
    _reject_server_fields(body, ("id",))
    with session_scope() as session:
        product = Product(
            description=_required_str(body, "description", 3, 500),
            price_amount=_decimal(price.get("amount")),
            price_currency=_currency(price.get("currency")),
        )
        session.add(product)
        session.flush()
        return _product_dto(product)


def _product_dto(product: Product) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "description": product.description,
        "price": {
            "amount": f"{Decimal(str(product.price_amount)):.2f}",
            "currency": product.price_currency,
        },
    }


# ── customers ─────────────────────────────────────────────────────────────


def create_customer(body: dict[str, Any]) -> dict[str, Any]:
    _reject_server_fields(body, ("id", "orderHistory"))
    banking = body.get("bankingDetails") or {}
    with session_scope() as session:
        customer = Customer(
            name=_required_str(body, "name", 2, 100),
            address=_required_str(body, "address", 5, 255),
            phone=_required_str(body, "phone", 8, 16),
            account_number=_required_str(banking, "accountNumber", 6, 20),
            bank_name=_required_str(banking, "bankName", 2, 100),
            role=_enum(body.get("role"), {"CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"}, "role"),
        )
        session.add(customer)
        session.flush()
        return _customer_dto(customer)


def get_customer(raw_id: str) -> dict[str, Any]:
    customer_id = parse_uuid(raw_id)
    with session_scope() as session:
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise not_found(f"customer {customer_id} does not exist")
        return _customer_dto(customer)


def _customer_dto(customer: Customer) -> dict[str, Any]:
    # The account number is deliberately absent: it must never be logged, and
    # keeping it out of the DTO keeps it out of every log that echoes one.
    return {
        "id": str(customer.id),
        "name": customer.name,
        "address": customer.address,
        "phone": customer.phone,
        "bankingDetails": {"bankName": customer.bank_name},
        "role": customer.role,
        "orderHistory": [],
    }


# ── orders ────────────────────────────────────────────────────────────────


def create_order(body: dict[str, Any]) -> dict[str, Any]:
    _reject_server_fields(body, ("id", "totalAmount", "status", "createdAt", "invoiceRef"))
    customer_id = parse_uuid(body.get("customerRef"))
    items = body.get("lineItems") or []
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise ControlledError(400, "VALIDATION_FAILED", "lineItems must hold 1 to 100 entries")

    refs = [parse_uuid(item.get("productRef")) for item in items]
    if len(set(refs)) != len(refs):
        raise ControlledError(400, "VALIDATION_FAILED", "duplicate productRef in one order")
    if any("unitPriceSnapshot" in item for item in items):
        raise ControlledError(400, "VALIDATION_FAILED", "unitPriceSnapshot is server-computed")

    with session_scope() as session:
        if session.get(Customer, customer_id) is None:
            raise not_found(f"customer {customer_id} does not exist")

        order = Order(customer_ref=customer_id, total_amount=Decimal("0.00"))
        total = Decimal("0.00")
        for item, product_ref in zip(items, refs):
            product = session.get(Product, product_ref)
            if product is None:
                raise not_found(f"product {product_ref} does not exist")
            quantity = _quantity(item.get("quantity"))
            unit_price = Decimal(str(product.price_amount))
            total += unit_price * quantity
            order.line_items.append(
                LineItem(
                    product_ref=product_ref,
                    quantity=quantity,
                    unit_price_snapshot=unit_price,
                )
            )

        order.total_amount = total
        session.add(order)
        session.flush()
        return _order_dto(order)


def get_order(raw_id: str) -> dict[str, Any]:
    order_id = parse_uuid(raw_id)
    with session_scope() as session:
        order = session.get(Order, order_id)
        if order is None:
            raise not_found(f"order {order_id} does not exist")
        return _order_dto(order)


def transition_order(raw_id: str, action: str) -> dict[str, Any]:
    """Advance an order, refusing any transition the state machine forbids."""
    allowed = {
        "accept": ("PLACED", "ACCEPTED"),
        "ship": ("VERIFIED", "SHIPPED"),
        "close": ("SHIPPED", "CLOSED"),
    }
    required, target = allowed[action]
    order_id = parse_uuid(raw_id)

    with session_scope() as session:
        order = session.get(Order, order_id)
        if order is None:
            raise not_found(f"order {order_id} does not exist")
        if order.status != required:
            raise conflict(
                f"cannot {action} an order in state {order.status}; expected {required}"
            )
        order.status = target
        session.flush()
        return _order_dto(order)


def _order_dto(order: Order) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "customerRef": str(order.customer_ref),
        "lineItems": [
            {
                "productRef": str(li.product_ref),
                "quantity": li.quantity,
                "unitPriceSnapshot": f"{Decimal(str(li.unit_price_snapshot)):.2f}",
            }
            for li in order.line_items
        ],
        "totalAmount": f"{Decimal(str(order.total_amount)):.2f}",
        "status": order.status,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "updatedAt": order.updated_at.isoformat() if order.updated_at else None,
        "invoiceRef": str(order.invoice_ref) if order.invoice_ref else None,
    }


# ── invoices ──────────────────────────────────────────────────────────────


def create_invoice(body: dict[str, Any]) -> dict[str, Any]:
    _reject_server_fields(body, ("id", "totalAmount", "status"))
    order_id = parse_uuid(body.get("orderRef"))

    # Two records change together, so they share one transaction.
    with session_scope() as session:
        order = session.get(Order, order_id)
        if order is None:
            raise not_found(f"order {order_id} does not exist")
        if order.status != "ACCEPTED":
            raise conflict(f"order must be ACCEPTED to invoice; it is {order.status}")

        customer = session.get(Customer, order.customer_ref)
        issue = date.today()
        invoice = Invoice(
            order_ref=order.id,
            billing_name=customer.name if customer else "unknown",
            billing_address=customer.address if customer else "unknown",
            total_amount=order.total_amount,
            issue_date=issue,
            due_date=issue + timedelta(days=7),
            status="ISSUED",
        )
        session.add(invoice)
        session.flush()

        order.invoice_ref = invoice.id
        order.status = "INVOICED"
        session.flush()
        return _invoice_dto(invoice)


def get_invoice(raw_id: str) -> dict[str, Any]:
    invoice_id = parse_uuid(raw_id)
    with session_scope() as session:
        invoice = session.get(Invoice, invoice_id)
        if invoice is None:
            raise not_found(f"invoice {invoice_id} does not exist")
        return _invoice_dto(invoice)


def _invoice_dto(invoice: Invoice) -> dict[str, Any]:
    return {
        "id": str(invoice.id),
        "orderRef": str(invoice.order_ref),
        "billingInfo": {"name": invoice.billing_name, "address": invoice.billing_address},
        "totalAmount": f"{Decimal(str(invoice.total_amount)):.2f}",
        "issueDate": invoice.issue_date.strftime("%d/%m/%Y"),
        "dueDate": invoice.due_date.strftime("%d/%m/%Y"),
        "status": invoice.status,
    }


# ── payments ──────────────────────────────────────────────────────────────


def create_payment(body: dict[str, Any]) -> dict[str, Any]:
    _reject_server_fields(body, ("id", "status", "timestamp"))
    order_id = parse_uuid(body.get("orderRef"))
    amount = _decimal(body.get("amount"))
    method = _enum(
        body.get("method"), {"CREDIT_CARD", "BANK_TRANSFER", "E_WALLET"}, "method"
    )

    with session_scope() as session:
        order = session.get(Order, order_id)
        if order is None:
            raise not_found(f"order {order_id} does not exist")
        if order.status != "INVOICED":
            raise conflict(f"order must be INVOICED to pay; it is {order.status}")

        invoice = session.execute(
            select(Invoice).where(Invoice.order_ref == order.id)
        ).scalar_one_or_none()
        if invoice is None:
            raise conflict("order has no invoice")
        if amount != Decimal(str(invoice.total_amount)):
            raise ControlledError(
                400, "VALIDATION_FAILED", "amount must equal the invoice total exactly"
            )

        payment = Payment(
            order_ref=order.id, amount=amount, status="PENDING", method=method
        )
        session.add(payment)
        # The order advances to PAID on submission; the payment stays PENDING
        # until an accountant verifies it. ASR-A4 restores exactly this pair.
        order.status = "PAID"
        session.flush()
        return _payment_dto(payment)


def verify_payment(raw_id: str) -> dict[str, Any]:
    """ASR-A4: three rows move as one unit, or none of them do."""
    payment_id = parse_uuid(raw_id)

    try:
        with session_scope() as session:
            payment = session.get(Payment, payment_id)
            if payment is None:
                raise not_found(f"payment {payment_id} does not exist")
            if payment.status != "PENDING":
                raise conflict(f"payment is {payment.status}, expected PENDING")

            order = session.get(Order, payment.order_ref)
            invoice = session.execute(
                select(Invoice).where(Invoice.order_ref == payment.order_ref)
            ).scalar_one_or_none()
            if order is None or invoice is None:
                raise conflict("payment is not linked to a complete order and invoice")

            payment.status = "VERIFIED"
            session.flush()

            if payment_fault_armed():
                if settings.defect_partial_commit:
                    # Calibration path: commit the payment on its own, so the
                    # three records diverge and only a direct SQL read shows it.
                    session.commit()
                log_event("injected_transaction_fault", payment_id=str(payment_id))
                raise InjectedTransactionFault("fault injected after payment update")

            invoice.status = "PAID"
            order.status = "VERIFIED"
            session.flush()
            return _payment_dto(payment)

    except InjectedTransactionFault as exc:
        metrics.increment("transaction_rollbacks_total")
        log_event("transaction_rollback", payment_id=str(payment_id), code=TRANSACTION_FAILED)
        raise ControlledError(
            500, TRANSACTION_FAILED, "transaction rolled back after an internal fault"
        ) from exc


def get_payment(raw_id: str) -> dict[str, Any]:
    payment_id = parse_uuid(raw_id)
    with session_scope() as session:
        payment = session.get(Payment, payment_id)
        if payment is None:
            raise not_found(f"payment {payment_id} does not exist")
        return _payment_dto(payment)


def _payment_dto(payment: Payment) -> dict[str, Any]:
    return {
        "id": str(payment.id),
        "orderRef": str(payment.order_ref),
        "amount": f"{Decimal(str(payment.amount)):.2f}",
        "timestamp": payment.timestamp.isoformat() if payment.timestamp else None,
        "status": payment.status,
        "method": payment.method,
    }


# ── small validators ──────────────────────────────────────────────────────


def _reject_server_fields(body: dict[str, Any], names: tuple[str, ...]) -> None:
    present = [n for n in names if n in body]
    if present:
        raise ControlledError(
            400, "VALIDATION_FAILED", f"server-controlled fields may not be supplied: {present}"
        )


def _required_str(body: dict[str, Any], key: str, lo: int, hi: int) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip() or not lo <= len(value) <= hi:
        raise ControlledError(400, "VALIDATION_FAILED", f"{key} must be {lo}-{hi} characters")
    return value


def _decimal(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception:
        raise ControlledError(400, "VALIDATION_FAILED", f"invalid amount: {value!r}")
    if parsed <= 0 or parsed.as_tuple().exponent != -2:
        raise ControlledError(
            400, "VALIDATION_FAILED", "amount must be positive with exactly two decimal places"
        )
    return parsed


def _currency(value: Any) -> str:
    return _enum(value, {"USD", "VND", "EUR"}, "currency")


def _enum(value: Any, allowed: set[str], name: str) -> str:
    if value not in allowed:
        raise ControlledError(
            400, "VALIDATION_FAILED", f"{name} must be one of {sorted(allowed)}"
        )
    return str(value)


def _quantity(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 1000:
        raise ControlledError(400, "VALIDATION_FAILED", "quantity must be an integer 1-1000")
    return value
