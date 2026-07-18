"""
Customer routes — /api/v1/customers

POST   /              Create customer
GET    /              List customers (paginated)
GET    /{id}          Get customer with order history
PUT    /{id}          Update customer
DELETE /{id}          Delete customer
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from oms.controllers.customer import customer_controller
from oms.database import get_session
from oms.schemas.customer import CustomerCreate, CustomerUpdate, CustomerRead, CustomerWithOrders
from oms.schemas.common import PaginatedResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=CustomerRead, status_code=201)
async def create_customer(data: CustomerCreate, session: AsyncSession = Depends(get_session)) -> CustomerRead:
    """Create a new customer."""
    return await customer_controller.create_customer(data, session)


@router.get("/", response_model=PaginatedResponse[CustomerRead])
async def list_customers(page: int = 1, page_size: int = 20, session: AsyncSession = Depends(get_session)) -> PaginatedResponse[CustomerRead]:
    """List all customers with pagination."""
    return await customer_controller.list_customers(session, page=page, page_size=page_size)


@router.get("/{customer_id}", response_model=CustomerWithOrders)
async def get_customer(customer_id: str, session: AsyncSession = Depends(get_session)) -> CustomerWithOrders:
    """Get a customer by ID with their order history."""
    return await customer_controller.get_customer(customer_id, session)


@router.put("/{customer_id}", response_model=CustomerRead)
async def update_customer(customer_id: str, data: CustomerUpdate, session: AsyncSession = Depends(get_session)) -> CustomerRead:
    """Update a customer's fields."""
    return await customer_controller.update_customer(customer_id, data, session)


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Delete a customer."""
    return await customer_controller.delete_customer(customer_id, session)