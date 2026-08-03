"""Repositories: plain data access over an injected Session.

Repositories deliberately contain no timeout, retry, or transaction logic. Those
are cross-cutting policies owned by app.persistence.database and applied around
whole units of work, so that they hold for every entity rather than being
duplicated (or forgotten) per repository.
"""

from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.core.test_hooks import InjectedTransientDbError, consume_transient_db_failure
from app.persistence.models import (
    Customer,
    Invoice,
    Order,
    OrderLineItem,
    Payment,
    Product,
)


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, customer: Customer) -> Customer:
        self._session.add(customer)
        self._session.flush()
        return customer

    def get(self, customer_id: uuid.UUID) -> Optional[Customer]:
        return self._session.get(Customer, customer_id)

    def order_ids(self, customer_id: uuid.UUID) -> list[uuid.UUID]:
        rows = self._session.execute(
            select(Order.id).where(Order.customer_id == customer_id).order_by(Order.created_at)
        ).scalars()
        return list(rows)


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, product: Product) -> Product:
        self._session.add(product)
        self._session.flush()
        return product

    def get(self, product_id: uuid.UUID) -> Optional[Product]:
        """Read a single Product at the instrumented database-read boundary.

        This is the boundary ASR-A2 observes. The attempt counter increments for
        every attempt that enters here - including injected transient failures -
        while db_product_reads_total increments only once the attempt is actually
        sent to PostgreSQL.
        """
        metrics.increment("db_product_read_attempts_total")
        if consume_transient_db_failure():
            raise InjectedTransientDbError(
                "injected transient database failure at the Product read boundary"
            )
        metrics.increment("db_product_reads_total")
        return self._session.get(Product, product_id)

    def search(self, query: Optional[str]) -> Sequence[Product]:
        metrics.increment("db_product_read_attempts_total")
        if consume_transient_db_failure():
            raise InjectedTransientDbError(
                "injected transient database failure at the Product read boundary"
            )
        metrics.increment("db_product_reads_total")
        statement = select(Product)
        if query:
            statement = statement.where(Product.description.ilike(f"%{query}%"))
        return list(self._session.execute(statement.order_by(Product.created_at)).scalars())

    def get_many(self, product_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, Product]:
        if not product_ids:
            return {}
        rows = self._session.execute(
            select(Product).where(Product.id.in_(list(product_ids)))
        ).scalars()
        return {product.id: product for product in rows}


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, order: Order) -> Order:
        self._session.add(order)
        self._session.flush()
        return order

    def add_line_item(self, item: OrderLineItem) -> OrderLineItem:
        self._session.add(item)
        self._session.flush()
        return item

    def get(self, order_id: uuid.UUID) -> Optional[Order]:
        return self._session.get(Order, order_id)


class InvoiceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, invoice: Invoice) -> Invoice:
        self._session.add(invoice)
        self._session.flush()
        return invoice

    def get(self, invoice_id: uuid.UUID) -> Optional[Invoice]:
        return self._session.get(Invoice, invoice_id)

    def get_by_order(self, order_id: uuid.UUID) -> Optional[Invoice]:
        return self._session.execute(
            select(Invoice).where(Invoice.order_id == order_id)
        ).scalar_one_or_none()


class PaymentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, payment: Payment) -> Payment:
        self._session.add(payment)
        self._session.flush()
        return payment

    def get(self, payment_id: uuid.UUID) -> Optional[Payment]:
        return self._session.get(Payment, payment_id)

    def get_by_order(self, order_id: uuid.UUID) -> Optional[Payment]:
        return self._session.execute(
            select(Payment).where(Payment.order_id == order_id)
        ).scalar_one_or_none()
