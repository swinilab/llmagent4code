"""Product controller."""
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import EntityId, get_product_service
from app.domain.models import ProductCreate, ProductRead
from app.services.services import ProductService

router = APIRouter(prefix="/products", tags=["products"])

Service = Annotated[ProductService, Depends(get_product_service)]


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    responses={400: {"description": "Field constraint violation"}, 429: {"description": "Rate limited"}},
)
async def create_product(payload: ProductCreate, service: Service) -> ProductRead:
    return await service.create(payload)


@router.get(
    "/{entity_id}",
    response_model=ProductRead,
    summary="Fetch a product by id",
    responses={400: {"description": "Malformed id"}, 404: {"description": "Not found"}},
)
async def get_product(entity_id: EntityId, service: Service) -> ProductRead:
    return await service.get(entity_id)
