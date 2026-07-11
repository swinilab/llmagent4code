"""Customer service — encapsulates business rules for customer management."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Customer, Product
from app.entities import CustomerEntity, ProductEntity
from app.repositories.customer_repo import CustomerRepository
from app.repositories.product_repo import ProductRepository


class CustomerService:
    """Handles customer and product lookups (read-heavy, cache-friendly)."""

    def __init__(self, session: AsyncSession) -> None:
        self._customer_repo = CustomerRepository(session)
        self._product_repo = ProductRepository(session)
        self._session = session

    async def create_customer(self, customer: Customer) -> Customer:
        entity = CustomerEntity(
            id=customer.id,
            name=customer.name,
            address=customer.address,
            phone=customer.phone,
            banking_details=customer.banking_details,
            role=customer.role.value,
        )
        saved = await self._customer_repo.save(entity)
        customer = Customer.model_validate(saved)
        # New customer has no orders yet, so order_history is empty
        customer.order_history = []
        return customer

    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        stmt = (
            select(CustomerEntity)
            .options(selectinload(CustomerEntity.orders))
            .where(CustomerEntity.id == customer_id)
        )
        result = await self._session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        customer = Customer.model_validate(entity)
        # Populate order_history from the orders relationship
        customer.order_history = [order.id for order in entity.orders]
        return customer

    async def list_customers(self) -> list[Customer]:
        stmt = select(CustomerEntity).options(selectinload(CustomerEntity.orders))
        result = await self._session.execute(stmt)
        entities = list(result.scalars().all())
        customers = []
        for entity in entities:
            customer = Customer.model_validate(entity)
            customer.order_history = [order.id for order in entity.orders]
            customers.append(customer)
        return customers

    async def create_product(self, product: Product) -> Product:
        entity = ProductEntity(
            id=product.id,
            description=product.description,
            base_price=product.base_price,
            currency=product.currency,
        )
        saved = await self._product_repo.save(entity)
        return Product.model_validate(saved)

    async def get_product(self, product_id: str) -> Optional[Product]:
        entity = await self._product_repo.get(product_id)
        return Product.model_validate(entity) if entity else None

    async def list_products(self) -> list[Product]:
        entities = await self._product_repo.list_all()
        return [Product.model_validate(e) for e in entities]