"""
Invoice REST controller.
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query

from app.infrastructure.queue_manager import QueueManager
from app.models.enums import InvoiceStatus
from app.schemas.invoice_schema import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
)
from app.services.invoice_service import InvoiceService


def create_invoice_router(
    dep_service: Callable[[], InvoiceService],
    queue_mgr: QueueManager | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])

    @router.post("", status_code=202)
    async def create_invoice(
        body: InvoiceCreate,
        service: InvoiceService = Depends(dep_service),
    ):
        """Step 3: Accountant creates invoice for accepted order (queued)."""
        if queue_mgr is None:
            # Fallback: process synchronously
            try:
                return await service.create_invoice(
                    order_id=body.order_id,
                    billing_info=body.billing_info,
                    due_days=body.due_days,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        enqueued = await queue_mgr.enqueue(
            task_type="create_invoice",
            payload={
                "order_id": body.order_id,
                "billing_info": body.billing_info,
                "due_days": body.due_days,
            },
            essential=True,
        )
        if not enqueued:
            raise HTTPException(status_code=503, detail="System busy, try again later")
        return {"status": "accepted", "message": "Invoice creation queued for processing"}

    @router.get("/{invoice_id}", response_model=InvoiceResponse)
    async def get_invoice(
        invoice_id: str,
        service: InvoiceService = Depends(dep_service),
    ):
        invoice = await service.get_invoice(invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice

    @router.get("", response_model=InvoiceListResponse)
    async def list_invoices(
        status: InvoiceStatus | None = Query(None),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=200),
        service: InvoiceService = Depends(dep_service),
    ):
        invoices, total = await service.list_invoices(
            status=status, skip=skip, limit=limit
        )
        return InvoiceListResponse(invoices=invoices, total=total)

    return router
