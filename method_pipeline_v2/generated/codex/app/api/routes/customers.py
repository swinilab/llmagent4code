from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_customer_controller
from app.controllers.common import missing_identifier
from app.controllers.customer_controller import CustomerController
from app.domain.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    controller: Annotated[CustomerController, Depends(get_customer_controller)],
) -> CustomerResponse:
    return await controller.create(body)


@router.get("", include_in_schema=False)
async def get_customer_without_id() -> None:
    missing_identifier()


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    controller: Annotated[CustomerController, Depends(get_customer_controller)],
) -> CustomerResponse:
    return await controller.get(customer_id)

