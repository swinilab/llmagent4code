"""Customer business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.customer import Customer
from src.repositories.customer import CustomerRepository
from src.schemas.customer import CustomerCreate, CustomerUpdate
from src.utils.exceptions import ConflictError, NotFoundError


class CustomerService:
    """Orchestrates customer CRUD with validation."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = CustomerRepository(session)

    async def create(self, payload: CustomerCreate) -> Customer:
        """Register a new customer, checking for phone uniqueness."""
        existing = await self.repo.get_by_phone(payload.phone)
        if existing:
            raise ConflictError(f"Customer with phone {payload.phone} already exists")
        customer = Customer(
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            banking_details=payload.banking_details,
            role=payload.role,
        )
        return await self.repo.add(customer)

    async def get(self, customer_id: str) -> Customer:
        """Retrieve a customer by ID."""
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundError(f"Customer {customer_id} not found")
        return customer

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Customer]:
        """List all customers with pagination."""
        return await self.repo.list_all(limit=limit, offset=offset)

    async def update(self, customer_id: str, payload: CustomerUpdate) -> Customer:
        """Partially update a customer."""
        customer = await self.get(customer_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        await self.repo.session.flush()
        return customer

    async def delete(self, customer_id: str) -> None:
        """Remove a customer."""
        customer = await self.get(customer_id)
        await self.repo.delete(customer)

    async def search(self, name_fragment: str) -> list[Customer]:
        """Search customers by name."""
        return await self.repo.search_by_name(name_fragment)
