"""
Invoice router for creating invoices.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.schemas import InvoiceCreateDTO
from app.services.invoice_service import issue_invoice_async

router = APIRouter()

@router.post("/invoice", status_code=status.HTTP_201_CREATED)
async def create_invoice(payload: InvoiceCreateDTO):
    try:
        invoice = await issue_invoice_async(
            order_id=payload.orderRef,
            billing_name=payload.billingInfo_name,
            billing_address=payload.billingInfo_address,
            issue_date_str=payload.issueDate,
            due_date_str=payload.dueDate,
        )
        return {"invoiceId": invoice.id, "status": invoice.status}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
