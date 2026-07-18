"""
Workflow REST controller — implements the 7-step OMS workflow as API endpoints.

Endpoints (all under /api/v1/workflow):
  POST /staff/accept/{order_id}         — Step 2: Staff accepts order
  POST /accountant/invoice              — Step 3: Accountant creates invoice
  POST /customer/pay                    — Step 4: Customer pays
  POST /accountant/verify/{payment_id}  — Step 5: Accountant verifies payment
  POST /staff/ship/{order_id}           — Step 6: Staff ships order
  POST /staff/close/{order_id}          — Step 7: Staff closes order
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.services.workflow import WorkflowService

router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow"])


class InvoiceRequest(BaseModel):
    """Payload for accountant invoice creation (Step 3)."""
    order_id: str
    billing_info: str = Field(..., min_length=1)
    due_date: date | None = None


class PaymentRequest(BaseModel):
    """Payload for customer payment (Step 4)."""
    order_id: str
    amount: str = Field(..., description="Decimal amount as string")
    method: str = Field(default="bank_transfer")


# ── Step 2: Staff accepts order ────────────────────────────
@router.post("/staff/accept/{order_id}")
async def staff_accept_order(order_id: str, session: AsyncSession = Depends(get_session)):
    """Order staff reviews and accepts a pending order."""
    svc = WorkflowService(session)
    return await svc.staff_accept_order(order_id)


# ── Step 3: Accountant creates invoice ─────────────────────
@router.post("/accountant/invoice", status_code=201)
async def accountant_create_invoice(
    payload: InvoiceRequest,
    session: AsyncSession = Depends(get_session),
):
    """Accountant creates an invoice for an accepted order."""
    svc = WorkflowService(session)
    return await svc.accountant_create_invoice(
        payload.order_id, payload.billing_info, payload.due_date
    )


# ── Step 4: Customer pays ──────────────────────────────────
@router.post("/customer/pay", status_code=201)
async def customer_pay(
    payload: PaymentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Customer submits payment for an invoiced order."""
    from decimal import Decimal

    svc = WorkflowService(session)
    return await svc.customer_pay(payload.order_id, Decimal(payload.amount), payload.method)


# ── Step 5: Accountant verifies payment ────────────────────
@router.post("/accountant/verify/{payment_id}")
async def accountant_verify_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Accountant verifies a payment and transitions order to PAID."""
    svc = WorkflowService(session)
    return await svc.accountant_verify_payment(payment_id)


# ── Step 6: Staff ships order ──────────────────────────────
@router.post("/staff/ship/{order_id}")
async def staff_ship_order(order_id: str, session: AsyncSession = Depends(get_session)):
    """Order staff ships a paid order."""
    svc = WorkflowService(session)
    return await svc.staff_ship_order(order_id)


# ── Step 7: Staff closes order ─────────────────────────────
@router.post("/staff/close/{order_id}")
async def staff_close_order(order_id: str, session: AsyncSession = Depends(get_session)):
    """Order staff closes a shipped order."""
    svc = WorkflowService(session)
    return await svc.staff_close_order(order_id)
