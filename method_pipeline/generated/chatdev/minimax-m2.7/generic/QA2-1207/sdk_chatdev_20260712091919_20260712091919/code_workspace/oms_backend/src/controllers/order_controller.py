"""
Order Controller - REST endpoints for order management.
Workflow: place -> accept -> invoice -> pay -> ship -> close
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session

from ..infrastructure.database import get_db
from ..services.order_service import OrderService, OrderWorkflowError
from ..domain.models import LineItem, Address, OrderStatus

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class AddressModel(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class LineItemModel(BaseModel):
    product_id: str
    product_description: str = ""
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    currency: str = "USD"


class PlaceOrderRequest(BaseModel):
    customer_id: str
    line_items: List[LineItemModel]
    shipping_address: AddressModel
    notes: str = ""
    idempotency_key: Optional[str] = None


class UpdateOrderRequest(BaseModel):
    notes: Optional[str] = None
    shipping: Optional[float] = Field(None, ge=0)


class MarkInvoicedRequest(BaseModel):
    invoice_id: str


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    line_items: List[dict]
    status: str
    subtotal: float
    tax: float
    shipping: float
    total: float
    currency: str
    invoice_id: Optional[str]
    shipping_address: Optional[dict]
    notes: str
    created_at: str
    updated_at: str
    accepted_at: Optional[str]
    shipped_at: Optional[str]
    completed_at: Optional[str]


def _to_response(order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        line_items=[li.to_dict() for li in order.line_items],
        status=order.status.value if hasattr(order.status, 'value') else order.status,
        subtotal=order.subtotal,
        tax=order.tax,
        shipping=order.shipping,
        total=order.total,
        currency=order.currency,
        invoice_id=order.invoice_id,
        shipping_address=order.shipping_address.to_dict() if order.shipping_address else None,
        notes=order.notes,
        created_at=order.created_at.isoformat(),
        updated_at=order.updated_at.isoformat(),
        accepted_at=order.accepted_at.isoformat() if order.accepted_at else None,
        shipped_at=order.shipped_at.isoformat() if order.shipped_at else None,
        completed_at=order.completed_at.isoformat() if order.completed_at else None
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    request: PlaceOrderRequest,
    db: Session = Depends(get_db)
):
    """Step 1: Customer places order."""
    service = OrderService(db)
    
    try:
        line_items = [
            LineItem(
                product_id=li.product_id,
                product_description=li.product_description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                currency=li.currency
            )
            for li in request.line_items
        ]
        
        shipping_address = Address.from_dict(request.shipping_address.dict())
        
        order = service.place_order(
            customer_id=request.customer_id,
            line_items=line_items,
            shipping_address=shipping_address,
            idempotency_key=request.idempotency_key,
            notes=request.notes
        )
        return _to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Get order by ID."""
    service = OrderService(db)
    order = service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_response(order)


@router.patch("/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Step 2: Order Staff accepts order."""
    service = OrderService(db)
    try:
        order = service.accept_order(order_id)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/reject", response_model=OrderResponse)
def reject_order(
    order_id: str,
    reason: str = "",
    db: Session = Depends(get_db)
):
    """Order Staff rejects order."""
    service = OrderService(db)
    try:
        order = service.reject_order(order_id, reason)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/invoiced", response_model=OrderResponse)
def mark_order_invoiced(
    order_id: str,
    request: MarkInvoicedRequest,
    db: Session = Depends(get_db)
):
    """Step 3: Order becomes invoiced after accountant creates invoice."""
    service = OrderService(db)
    try:
        order = service.mark_invoiced(order_id, request.invoice_id)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/paid", response_model=OrderResponse)
def mark_order_paid(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Step 5: Order becomes paid after accountant verifies payment."""
    service = OrderService(db)
    try:
        order = service.mark_paid(order_id)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/ship", response_model=OrderResponse)
def ship_order(
    order_id: str,
    tracking_number: str = "",
    db: Session = Depends(get_db)
):
    """Step 6: Order Staff ships paid order."""
    service = OrderService(db)
    try:
        order = service.ship_order(order_id, tracking_number)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/close", response_model=OrderResponse)
def close_order(
    order_id: str,
    db: Session = Depends(get_db)
):
    """Step 7: Order Staff closes completed order."""
    service = OrderService(db)
    try:
        order = service.close_order(order_id)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    reason: str = "",
    db: Session = Depends(get_db)
):
    """Cancel an order (only if not yet shipped)."""
    service = OrderService(db)
    try:
        order = service.cancel_order(order_id, reason)
        return _to_response(order)
    except OrderWorkflowError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[OrderResponse])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List orders with optional filters."""
    service = OrderService(db)
    
    if status:
        orders = service.get_orders_by_status(status, skip=skip, limit=limit)
    elif customer_id:
        orders = service.get_orders_by_customer(customer_id, skip=skip, limit=limit)
    else:
        orders = service.repo.get_all(skip=skip, limit=limit)
    
    return [_to_response(o) for o in orders]


@router.get("/pending", response_model=List[OrderResponse])
def list_pending_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get orders pending review (for order staff)."""
    service = OrderService(db)
    orders = service.get_pending_orders(skip=skip, limit=limit)
    return [_to_response(o) for o in orders]


@router.get("/recovery/pending", response_model=List[dict])
def get_recovery_pending(
    db: Session = Depends(get_db)
):
    """Get orders that may need recovery (NFR 2.3 verification)."""
    service = OrderService(db)
    orders = service.recover_pending_orders()
    return [
        {"order_id": o.id, "status": o.status.value if hasattr(o.status, 'value') else o.status}
        for o in orders
    ]
