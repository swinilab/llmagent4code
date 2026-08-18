"""Customer controller - REST endpoints, request/response mapping."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import EntityId, get_customer_service
from app.domain.models import CustomerCreate, CustomerRead
from app.services.services import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])

Service = Annotated[CustomerService, Depends(get_customer_service)]


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer",
    responses={400: {"description": "Field constraint violation"}, 429: {"description": "Rate limited"}},
)
async def create_customer(payload: CustomerCreate, service: Service) -> CustomerRead:
    return await service.create(payload)


@router.get(
    "/{entity_id}",
    response_model=CustomerRead,
    summary="Fetch a customer by id",
    responses={400: {"description": "Malformed id"}, 404: {"description": "Not found"}},
)
async def get_customer(entity_id: EntityId, service: Service) -> CustomerRead:
    return await service.get(entity_id)
