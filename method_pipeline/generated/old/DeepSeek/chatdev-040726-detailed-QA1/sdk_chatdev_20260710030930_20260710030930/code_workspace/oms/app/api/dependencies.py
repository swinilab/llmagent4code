"""FastAPI dependency injection for services and repositories.

Uses a UnitOfWork pattern to ensure all repositories within a single
request share the same database session, providing transactional
consistency across multi-repository operations (NFR 1.1, NFR 1.2).
"""

from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_session
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.product_repo import ProductRepository
from app.services.order_service import OrderService
from app.services.product_service import ProductService


@dataclass
class UnitOfWork:
    """Single-session unit of work containing all repositories.

    All repository operations within a single request share the same
    AsyncSession, ensuring atomic commits/rollbacks across the entire
    unit of work. This prevents the critical bug where separate sessions
    per repository would cause partial writes (e.g., payment saved but
    order not updated) under concurrent or failure scenarios.
    """

    session: AsyncSession
    orders: OrderRepository
    products: ProductRepository
    payments: PaymentRepository
    invoices: InvoiceRepository


async def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    """Provide a unit of work with a shared session across all repositories.

    FastAPI caches the result of Depends(get_session) within a single
    request scope, so all repositories receive the same AsyncSession
    instance. The session's commit/rollback in get_session() then
    atomically persists or discards all changes made across repositories.
    """
    return UnitOfWork(
        session=session,
        orders=OrderRepository(session),
        products=ProductRepository(session),
        payments=PaymentRepository(session),
        invoices=InvoiceRepository(session),
    )


async def get_order_service(uow: UnitOfWork = Depends(get_uow)) -> OrderService:
    return OrderService(
        order_repo=uow.orders,
        product_repo=uow.products,
        payment_repo=uow.payments,
        invoice_repo=uow.invoices,
    )


async def get_product_service(uow: UnitOfWork = Depends(get_uow)) -> ProductService:
    return ProductService(product_repo=uow.products)
