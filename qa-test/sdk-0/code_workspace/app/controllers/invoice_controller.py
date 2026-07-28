from fastapi import APIRouter, HTTPException
import uuid

from app.models import InvoiceCreateDTO, InvoiceDTO
from app.services.invoice_service import InvoiceService

router = APIRouter()

@router.post('', response_model=InvoiceDTO)
def create_invoice(dto: InvoiceCreateDTO):
    return InvoiceService.create_invoice(dto)

@router.post('/{invoice_id}/verify')
def verify_invoice(invoice_id: str):
    return InvoiceService.verify_invoice(invoice_id)
