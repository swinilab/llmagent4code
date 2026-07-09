"""
Customer service — CRUD for customer accounts.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Customer
from app.domain.schemas import CustomerCreate
from app.repositories.customer import CustomerRepository


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CustomerRepository(session)

    async def create_customer(self, data: CustomerCreate) -> Customer:
        customer = Customer(
            name=data.name,
            address=data.address,
            phone=data.phone,
            banking_details=data.banking_details,
            role=data.role,
        )
        return await self._repo.add(customer)

    async def get_customer(self, customer_id: int) -> Customer:
        return await self._repo.get_or_fail(customer_id)

    async def list_customers(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Customer], int]:
        return await self._repo.list(
            offset=(page - 1) * page_size,
            limit=page_size,
            order_by=Customer.id,
        )
