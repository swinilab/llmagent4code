from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_product_controller
from app.controllers.common import missing_identifier
from app.controllers.product_controller import ProductController
from app.domain.schemas import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    controller: Annotated[ProductController, Depends(get_product_controller)],
) -> ProductResponse:
    return await controller.create(body)


@router.get("", include_in_schema=False)
async def get_product_without_id() -> None:
    missing_identifier()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    controller: Annotated[ProductController, Depends(get_product_controller)],
) -> ProductResponse:
    return await controller.get(product_id)

