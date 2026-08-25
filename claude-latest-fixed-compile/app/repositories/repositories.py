"""Repository layer.

A single generic ``SQLAlchemyRepository`` supplies the CRUD shape; the per-entity
repositories add only the queries unique to them (composition over inheritance -
the shared behaviour lives in one place rather than being copied per entity).

Repositories never open transactions. They receive a Session owned by the
service layer, which is what makes a multi-entity workflow step commit or roll
back as one unit (NFR 2.4).
"""
import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.repositories.schema import Base, Customer, Invoice, Order, OrderLineItem, Payment, Product

ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()  # assigns the PK without ending the transaction
        return entity

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def get_for_update(self, entity_id: uuid.UUID) -> ModelT | None:
        """Row-level pessimistic lock - serialises concurrent state transitions."""
        stmt = select(self.model).where(self.model.id == entity_id).with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def list(self, limit: int = 50, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars())

    def count(self) -> int:
        return int(self.session.execute(select(func.count()).select_from(self.model)).scalar_one())


class CustomerRepository(SQLAlchemyRepository[Customer]):
    model = Customer

    def get_active(self, customer_id: uuid.UUID) -> Customer | None:
        """Existence check honouring the 'non-deleted customer' rule."""
        stmt = select(Customer).where(Customer.id == customer_id, Customer.deleted.is_(False))
        return self.session.execute(stmt).scalar_one_or_none()

    def order_history(self, customer_id: uuid.UUID, cap: int = 10_000) -> list[uuid.UUID]:
        stmt = (
            select(Order.id)
            .where(Order.customer_ref == customer_id)
            .order_by(Order.created_at.desc())
            .limit(cap)
        )
        return list(self.session.execute(stmt).scalars())


class ProductRepository(SQLAlchemyRepository[Product]):
    model = Product

    def get_many(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, Product]:
        """Single round-trip fetch for order pricing (avoids N+1 per line item)."""
        if not ids:
            return {}
        stmt = select(Product).where(Product.id.in_(ids))
        return {p.id: p for p in self.session.execute(stmt).scalars()}


class OrderRepository(SQLAlchemyRepository[Order]):
    model = Order

    def add_line_item(self, item: OrderLineItem) -> OrderLineItem:
        self.session.add(item)
        return item

    def by_status(self, status: str, limit: int = 50) -> list[Order]:
        stmt = select(Order).where(Order.status == status).limit(limit)
        return list(self.session.execute(stmt).scalars())


class InvoiceRepository(SQLAlchemyRepository[Invoice]):
    model = Invoice

    def get_by_order(self, order_ref: uuid.UUID) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.order_ref == order_ref)
        return self.session.execute(stmt).scalar_one_or_none()

    def overdue_before(self, today) -> list[Invoice]:
        stmt = select(Invoice).where(Invoice.status == "ISSUED", Invoice.due_date < today)
        return list(self.session.execute(stmt).scalars())


class PaymentRepository(SQLAlchemyRepository[Payment]):
    model = Payment

    def get_by_order(self, order_ref: uuid.UUID) -> list[Payment]:
        stmt = select(Payment).where(Payment.order_ref == order_ref)
        return list(self.session.execute(stmt).scalars())

    def has_settled_payment(self, order_ref: uuid.UUID) -> bool:
        """Blocks double payment: any PENDING or VERIFIED payment occupies the order."""
        stmt = select(func.count()).select_from(Payment).where(
            Payment.order_ref == order_ref, Payment.status.in_(("PENDING", "VERIFIED"))
        )
        return int(self.session.execute(stmt).scalar_one()) > 0
