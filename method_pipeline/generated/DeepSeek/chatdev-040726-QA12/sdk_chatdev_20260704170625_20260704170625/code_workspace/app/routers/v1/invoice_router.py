"""Invoice REST controller — v1 API.

Uses WorkflowService to orchestrate the full lifecycle transitions.
WorkflowError propagates to the global handler in main.py for ACID compliance.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.models import Invoice
from app.services.invoice_service import InvoiceService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/v1/invoices", tags=["Invoices"])


class CreateInvoiceRequest(BaseModel):
    order_id: str
    customer_id: str
    billing_name: str
    billing_address: str
    total_amount: Decimal
    due_days: int = 30


class StatusUpdateResponse(BaseModel):
    invoice: Invoice
    message: str


@router.post("", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(body: CreateInvoiceRequest, db: AsyncSession = Depends(get_db)):
    """Accountant creates invoice for an accepted order (Step 3)."""
    workflow = WorkflowService(db)
    invoice = await workflow.create_invoice(
        order_id=body.order_id,
        customer_id=body.customer_id,
        billing_name=body.billing_name,
        billing_address=body.billing_address,
        total_amount=body.total_amount,
        due_days=body.due_days,
    )
    if invoice is None:
        raise HTTPException(
            status_code=409,
            detail="Invoice cannot be created. Order must be in ACCEPTED state.",
        )
    return invoice


@router.get("", response_model=list[Invoice])
async def list_invoices(db: AsyncSession = Depends(get_db)):
    svc = InvoiceService(db)
    return await svc.list_invoices()


@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    svc = InvoiceService(db)
    invoice = await svc.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/{invoice_id}/pay", response_model=StatusUpdateResponse)
async def pay_invoice(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Customer pays the invoice (Step 4).

    WorkflowError propagates to the global exception handler, which
    returns a 409 response only AFTER the DB transaction is rolled back
    by get_db(), preserving ACID guarantees.
    """
    workflow = WorkflowService(db)
    invoice = await workflow.pay_invoice(invoice_id)
    return StatusUpdateResponse(invoice=invoice, message="Invoice paid and order marked as PAID")