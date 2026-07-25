"""
Order controller with REST endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
from app.db.connection_pool import get_db
from app.db.connection_pool import get_db
from app.services.order_service import OrderService, OrderValidationError, OrderTransitionError
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


class LineItemRequest(BaseModel):
    """Request model for line item"""
    productRef: str
    quantity: int = Field(..., ge=1, le=1000)


class OrderCreateRequest(BaseModel):
    """Request model for creating an order"""
    customerRef: str
    lineItems: List[LineItemRequest] = Field(..., min_length=1, max_length=100)
class OrderResponse(BaseModel):
    """Response model for order"""
    id: str
    customerRef: str
    lineItems: List[dict]
    totalAmount: str
    status: str
    createdAt: str
    updatedAt: str
    invoiceRef: Optional[str] = None


@router.post("", response_model=OrderResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_order(request: OrderCreateRequest, session: AsyncSession = Depends(get_db)):
    service = OrderService(session)
    try:
        line_items = [{"productRef": item.productRef, "quantity": item.quantity} for item in request.lineItems]
        order = await service.create_order(request.customerRef, line_items)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=List[OrderResponse])
async def list_orders(limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_db)):
    """List all orders"""
    service = OrderService(session)
    orders = await service.get_all_orders(limit, offset)
    return [
        OrderResponse(
            id=str(o.id),
            customerRef=str(o.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in o.lineItems
            ],
            totalAmount=str(o.totalAmount),
            status=o.status,
            createdAt=o.createdAt.isoformat(),
            updatedAt=o.updatedAt.isoformat(),
            invoiceRef=str(o.invoiceRef) if o.invoiceRef else None,
        )
        for o in orders
    ]


@router.get("/recent", response_model=List[OrderResponse])
async def get_recent_orders(limit: int = 1, session: AsyncSession = Depends(get_db)):
    """Get most recent orders (for resolving async creates)"""
    service = OrderService(session)
    orders = await service.get_most_recent_orders(limit)
    return [
        OrderResponse(
            id=str(o.id),
            customerRef=str(o.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in o.lineItems
            ],
            totalAmount=str(o.totalAmount),
            status=o.status,
            createdAt=o.createdAt.isoformat(),
            updatedAt=o.updatedAt.isoformat(),
            invoiceRef=str(o.invoiceRef) if o.invoiceRef else None,
        )
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Get order by ID"""
    service = OrderService(session)
    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=str(order.id),
        customerRef=str(order.customerRef),
        lineItems=[
            {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
            for item in order.lineItems
        ],
        totalAmount=str(order.totalAmount),
        status=order.status,
        createdAt=order.createdAt.isoformat(),
        updatedAt=order.updatedAt.isoformat(),
        invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
    )


@router.put("/{order_id}/review", response_model=OrderResponse)
async def review_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Review order"""
    service = OrderService(session)
    try:
        order = await service.review_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Accept order (PLACED -> ACCEPTED)"""
    service = OrderService(session)
    try:
        order = await service.accept_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Cancel order"""
    service = OrderService(session)
    try:
        order = await service.cancel_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
@router.put("/{order_id}/verify", response_model=OrderResponse)
async def verify_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Verify order (PAID -> VERIFIED)"""
    service = OrderService(session)
    try:
        order = await service.verify_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Ship order (VERIFIED -> SHIPPED)"""
    service = OrderService(session)
    try:
        order = await service.ship_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{order_id}/close", response_model=OrderResponse)
async def close_order(order_id: str, session: AsyncSession = Depends(get_db)):
    """Close order (SHIPPED -> CLOSED)"""
    service = OrderService(session)
    try:
        order = await service.close_order(order_id)
        return OrderResponse(
            id=str(order.id),
            customerRef=str(order.customerRef),
            lineItems=[
                {"productRef": str(item.productRef), "quantity": item.quantity, "unitPriceSnapshot": str(item.unitPriceSnapshot)}
                for item in order.lineItems
            ],
            totalAmount=str(order.totalAmount),
            status=order.status,
            createdAt=order.createdAt.isoformat(),
            updatedAt=order.updatedAt.isoformat(),
            invoiceRef=str(order.invoiceRef) if order.invoiceRef else None,
        )
    except OrderValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrderTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
