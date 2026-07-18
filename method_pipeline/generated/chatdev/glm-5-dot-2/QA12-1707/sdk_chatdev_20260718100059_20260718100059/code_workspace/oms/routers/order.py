"""
Order routes — /api/v1/orders

POST   /                        Create order (step 1: customer places order)
GET    /                        List orders (paginated, optional status filter)
GET    /{id}                    Get order with all details
PUT    /{id}/items              Update order line items (only when PENDING)
POST   /{id}/transition         Transition order status (steps 2, 6, 7)
POST   /{id}/cancel             Cancel order
DELETE /{id}                    Delete order
GET    /customer/{customer_id}  List orders for a customer
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from oms.controllers.order import order_controller
from oms.database import get_session
from oms.enums import OrderStatus
from oms.schemas.order import OrderCreate, OrderUpdate, OrderRead, OrderStatusUpdate
from oms.schemas.common import PaginatedResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=201)
async def create_order(data: OrderCreate, session: AsyncSession = Depends(get_session)) -> OrderRead:
    """Create a new order with line items (step 1: customer places order)."""
    return await order_controller.create_order(data, session)


@router.get("/", response_model=PaginatedResponse[OrderRead])
async def list_orders(
    page: int = 1, page_size: int = 20,
    status: OrderStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[OrderRead]:
    """List all orders with optional status filter and pagination."""
    return await order_controller.list_orders(session, page=page, page_size=page_size, status=status)


@router.get("/customer/{customer_id}", response_model=PaginatedResponse[OrderRead])
async def list_customer_orders(
    customer_id: str, page: int = 1, page_size: int = 20,
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[OrderRead]:
    """List all orders for a specific customer."""
    return await order_controller.list_customer_orders(customer_id, session, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: str, session: AsyncSession = Depends(get_session)) -> OrderRead:
    """Get an order by ID with all nested details."""
    return await order_controller.get_order(order_id, session)


@router.put("/{order_id}/items", response_model=OrderRead)
async def update_order_items(order_id: str, data: OrderUpdate, session: AsyncSession = Depends(get_session)) -> OrderRead:
    """Replace all line items on a PENDING order."""
    return await order_controller.update_order_items(order_id, data, session)


@router.post("/{order_id}/transition", response_model=OrderRead)
async def transition_order_status(order_id: str, data: OrderStatusUpdate, session: AsyncSession = Depends(get_session)) -> OrderRead:
    """
    Transition an order to a new status.
    Workflow steps:
    - PENDING to ACCEPTED (step 2: order staff reviews & accepts)
    - ACCEPTED to INVOICED (step 3: handled by invoice creation)
    - INVOICED to PAID (step 5: handled by payment verification)
    - PAID to SHIPPED (step 6: order staff ships)
    - SHIPPED to CLOSED (step 7: order staff closes)
    """
    return await order_controller.transition_status(order_id, data, session)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(order_id: str, reason: str | None = None, session: AsyncSession = Depends(get_session)) -> OrderRead:
    """Cancel an order (only from PENDING or ACCEPTED)."""
    return await order_controller.cancel_order(order_id, session, reason=reason)


@router.delete("/{order_id}")
async def delete_order(order_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    """Delete an order."""
    return await order_controller.delete_order(order_id, session)