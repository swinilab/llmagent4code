from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_invoice_controller
from app.controllers.common import missing_identifier
from app.controllers.invoice_controller import InvoiceController
from app.domain.schemas import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    controller: Annotated[InvoiceController, Depends(get_invoice_controller)],
) -> InvoiceResponse:
    return await controller.create(body)


@router.get("", include_in_schema=False)
async def get_invoice_without_id() -> None:
    missing_identifier()


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    controller: Annotated[InvoiceController, Depends(get_invoice_controller)],
) -> InvoiceResponse:
    return await controller.get(invoice_id)

