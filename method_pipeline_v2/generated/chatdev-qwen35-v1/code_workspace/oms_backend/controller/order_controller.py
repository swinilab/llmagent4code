"""
Order controller
REST endpoints for order operations
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oms_backend.infrastructure.database import get_db
from oms_backend.service import OrderService
from oms_backend.domain.models import Order, OrderCreate
from oms_backend.controller.responses import ErrorResponse
from oms_backend.utils.exceptions import OMSException, NotFoundException, ValidationException, ConflictException
from oms_backend.utils.rate_limiter import rate_limiter


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        404: {"model": ErrorResponse, "description": "Customer or product not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create a new order",
    description="Create a new order (Customer places order). Initial status is PLACED.",
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new order.
    NFR 1.1: Rate limiting applied.
    NFR 2.4: Transaction ensures atomic creation.
    """
    if not rate_limiter.is_allowed("create_order"):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": 60}
        )
    
    service = OrderService(db)
    try:
        return service.create_order(data)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ValidationException as e:
        raise HTTPException(status_code=400, detail={"message": e.message, "field": e.field})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "",
    response_model=List[Order],
    summary="Get all orders",
    description="Retrieve a list of all orders.",
)
def get_all_orders(db: Session = Depends(get_db)):
    """Get all orders."""
    service = OrderService(db)
    return service.get_all_orders()


@router.get(
    "/{order_id}",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
    summary="Get order by ID",
    description="Retrieve an order by their unique ID.",
)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get order by ID."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.get_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.get(
    "/customer/{customer_id}",
    response_model=List[Order],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
    },
    summary="Get orders by customer",
    description="Retrieve all orders for a specific customer.",
)
def get_orders_by_customer(customer_id: str, db: Session = Depends(get_db)):
    """Get orders by customer ID."""
    try:
        uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    return service.get_orders_by_customer(uuid)


@router.post(
    "/{order_id}/accept",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Accept order",
    description="Order Staff reviews and accepts the order. Transitions from PLACED to ACCEPTED.",
)
def accept_order(order_id: str, db: Session = Depends(get_db)):
    """Accept order (Order Staff action)."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.accept_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{order_id}/cancel",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Cancel order",
    description="Cancel an order. Can be cancelled from PLACED, ACCEPTED, or INVOICED state.",
)
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """Cancel order."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.cancel_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{order_id}/verify",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Verify order",
    description="Verify order after payment verification. Transitions from PAID to VERIFIED.",
)
def verify_order(order_id: str, db: Session = Depends(get_db)):
    """Verify order."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.verify_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{order_id}/ship",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Ship order",
    description="Order Staff ships the paid order. Transitions from VERIFIED to SHIPPED.",
)
def ship_order(order_id: str, db: Session = Depends(get_db)):
    """Ship order (Order Staff action)."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.ship_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})


@router.post(
    "/{order_id}/close",
    response_model=Order,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid UUID format"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {"model": ErrorResponse, "description": "Invalid state transition"},
    },
    summary="Close order",
    description="Order Staff closes the completed order. Transitions from SHIPPED to CLOSED.",
)
def close_order(order_id: str, db: Session = Depends(get_db)):
    """Close order (Order Staff action)."""
    try:
        uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"message": "Invalid UUID format"})
    
    service = OrderService(db)
    try:
        return service.close_order(uuid)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail={"message": e.message})
    except ConflictException as e:
        raise HTTPException(
            status_code=409,
            detail={"message": e.message, "current_state": e.current_state, "expected_state": e.expected_state}
        )
    except OMSException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message})
