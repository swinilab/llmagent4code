"""
Payment routes — /api/v1/payments

POST   /              Create payment (step 4: customer pays invoice)
GET    /              List payments (paginated)
GET    /{id}          Get payment
POST   /{id}/verify   Verify/reject payment (step 5: accountant verifies)
GET    /order/{id}    List payments for an order
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from oms.controllers.payment import payment_controller
from oms.database import get_session
from oms.schemas.payment import PaymentCreate, PaymentRead, PaymentVerify
from oms.schemas.common import PaginatedResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentRead, status_code=201)
async def create_payment(data: PaymentCreate, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    """Create a payment for an order's invoice (step 4: customer pays)."""
    return await payment_controller.create_payment(data, session)


@router.get("/", response_model=PaginatedResponse[PaymentRead])
async def list_payments(page: int = 1, page_size: int = 20, session: AsyncSession = Depends(get_session)) -> PaginatedResponse[PaymentRead]:
    """List all payments with pagination."""
    return await payment_controller.list_payments(session, page=page, page_size=page_size)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: str, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    """Get a payment by ID."""
    return await payment_controller.get_payment(payment_id, session)


@router.post("/{payment_id}/verify", response_model=PaymentRead)
async def verify_payment(payment_id: str, data: PaymentVerify, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    """Verify or reject a payment (step 5: accountant verifies)."""
    return await payment_controller.verify_payment(payment_id, data, session)


@router.get("/order/{order_id}", response_model=list[PaymentRead])
async def list_order_payments(order_id: str, session: AsyncSession = Depends(get_session)) -> list[PaymentRead]:
    """List all payments for a specific order."""
    return await payment_controller.list_order_payments(order_id, session)