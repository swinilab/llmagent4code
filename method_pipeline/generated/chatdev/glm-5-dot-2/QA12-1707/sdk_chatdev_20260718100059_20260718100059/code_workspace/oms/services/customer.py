"""
Customer service — business logic for customer management.

Handles creation, updates, retrieval with order history, and deletion.
Transaction boundaries are managed at the service layer.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from oms.repositories.customer import CustomerRepository
from oms.schemas.customer import CustomerCreate, CustomerUpdate
from oms.models.customer import Customer

logger = logging.getLogger(__name__)


class CustomerService:
    """Business logic for Customer entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CustomerRepository(session)

    async def create_customer(self, data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = await self.repo.create(
            name=data.name,
            address=data.address,
            phone=data.phone,
            banking_details=data.banking_details,
            role=data.role,
        )
        await self.session.commit()
        logger.info("Created customer %s (%s)", customer.id, customer.name)
        return customer

    async def get_customer(self, customer_id: str) -> Customer | None:
        """Fetch a customer by ID."""
        return await self.repo.get_by_id(customer_id)

    async def get_customer_with_orders(self, customer_id: str) -> Customer | None:
        """Fetch a customer with their order history."""
        return await self.repo.get_with_orders(customer_id)

    async def list_customers(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Customer], int]:
        """List customers with pagination."""
        offset = (page - 1) * page_size
        return await self.repo.get_all(offset=offset, limit=page_size)

    async def update_customer(
        self, customer_id: str, data: CustomerUpdate
    ) -> Customer | None:
        """Update a customer's fields."""
        customer = await self.repo.get_by_id(customer_id)
        if customer is None:
            return None
        updates = data.model_dump(exclude_unset=True)
        customer = await self.repo.update(customer, **updates)
        await self.session.commit()
        logger.info("Updated customer %s", customer_id)
        return customer

    async def delete_customer(self, customer_id: str) -> bool:
        """Delete a customer. Returns True if deleted, False if not found."""
        customer = await self.repo.get_by_id(customer_id)
        if customer is None:
            return False
        await self.repo.delete(customer)
        await self.session.commit()
        logger.info("Deleted customer %s", customer_id)
        return True