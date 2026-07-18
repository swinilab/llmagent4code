"""
Customer controller — REST endpoint handlers for customer operations.

Maps HTTP requests to service calls and returns Pydantic response models.
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from oms.schemas.customer import CustomerCreate, CustomerUpdate, CustomerRead, CustomerWithOrders
from oms.schemas.common import PaginatedResponse
from oms.services.customer import CustomerService


class CustomerController:
    """Handles customer CRUD endpoints."""

    async def create_customer(self, data: CustomerCreate, session: AsyncSession) -> CustomerRead:
        service = CustomerService(session)
        customer = await service.create_customer(data)
        return CustomerRead.model_validate(customer)

    async def get_customer(self, customer_id: str, session: AsyncSession) -> CustomerWithOrders:
        service = CustomerService(session)
        customer = await service.get_customer_with_orders(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        return CustomerWithOrders.model_validate(customer)

    async def list_customers(self, session: AsyncSession, page: int = 1, page_size: int = 20) -> PaginatedResponse[CustomerRead]:
        service = CustomerService(session)
        items, total = await service.list_customers(page=page, page_size=page_size)
        return PaginatedResponse[CustomerRead].create(
            items=[CustomerRead.model_validate(c) for c in items],
            total=total, page=page, page_size=page_size,
        )

    async def update_customer(self, customer_id: str, data: CustomerUpdate, session: AsyncSession) -> CustomerRead:
        service = CustomerService(session)
        customer = await service.update_customer(customer_id, data)
        if customer is None:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        return CustomerRead.model_validate(customer)

    async def delete_customer(self, customer_id: str, session: AsyncSession) -> dict:
        service = CustomerService(session)
        deleted = await service.delete_customer(customer_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        return {"deleted": True, "id": customer_id}


customer_controller = CustomerController()