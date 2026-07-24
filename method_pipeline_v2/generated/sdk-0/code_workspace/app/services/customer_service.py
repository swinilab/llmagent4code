"""
Customer service — business logic for customer management.
"""
from __future__ import annotations

from app.models.enums import UserRole
from app.repositories.customer_repo import CustomerRepository
from app.schemas.customer_schema import CustomerResponse


class CustomerService:
    def __init__(self, repo: CustomerRepository) -> None:
        self._repo = repo

    async def create_customer(
        self,
        name: str,
        address: str,
        phone: str,
        banking_details: str,
        role: UserRole = UserRole.CUSTOMER,
    ) -> CustomerResponse:
        customer = await self._repo.create(
            name=name,
            address=address,
            phone=phone,
            banking_details=banking_details,
            role=role,
        )
        return CustomerResponse.model_validate(customer)

    async def get_customer(self, customer_id: str) -> CustomerResponse | None:
        customer = await self._repo.get(customer_id)
        if customer is None:
            return None
        return CustomerResponse.model_validate(customer)

    async def list_customers(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[CustomerResponse], int]:
        customers = await self._repo.list_all(skip=skip, limit=limit)
        total = await self._repo.count()
        return [CustomerResponse.model_validate(c) for c in customers], total
