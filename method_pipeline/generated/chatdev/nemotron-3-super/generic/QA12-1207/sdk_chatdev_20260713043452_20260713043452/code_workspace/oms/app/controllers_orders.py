from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, crud, services
from app.database import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order (customer places order).
    """
    # Check if customer exists
    customer = await crud.get_customer(db, customer_id=order_in.customer_id)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )
    # Check if order number already exists
    existing_order = await crud.get_order_by_number(db, order_number=order_in.order_number)
    if existing_order:
        raise HTTPException(
            status_code=400,
            detail="Order number already exists",
        )
    return await crud.create_order(db, order_in=order_in)


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve orders.
    """
    orders = await crud.get_orders(db, skip=skip, limit=limit)
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
async def read_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific order by ID.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=schemas.Order)
async def update_order(
    order_id: int,
    order_in: schemas.OrderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an order.
    """
    order = await crud.update_order(db, order_id=order_id, order_in=order_in)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", response_model=schemas.Order)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an order.
    """
    order = await crud.delete_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# Workflow endpoints
@router.post("/{order_id}/items", response_model=schemas.OrderItem)
async def add_item_to_order(
    order_id: int,
    product_id: int,
    quantity: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a product to an order.
    """
    # Check order exists and is in editable state (pending or accepted?)
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # Typically items can be added while order is pending or accepted
    if order.status not in [schemas.OrderStatusEnum.PENDING, schemas.OrderStatusEnum.ACCEPTED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add items to order in {order.status} status",
        )
    # Check product exists
    product = await crud.get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not product.is_active:
        raise HTTPException(status_code=400, detail="Product is not active")
    
    return await services.add_item_to_order(
        db, order_id=order_id, product_id=product_id, quantity=quantity
    )


@router.post("/{order_id}/review", response_model=schemas.Order)
async def review_order(
    order_id: int,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Order staff reviews and accepts the order.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not in pending status (current: {order.status})",
        )
    return await services.review_order_service(
        db, order_id=order_id, notes=notes
    )


@router.post("/{order_id}/invoice", response_model=schemas.Order)
async def create_invoice(
    order_id: int,
    invoice_number: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Accountant creates invoice for accepted order.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.ACCEPTED:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not accepted (current: {order.status})",
        )
    # Check if invoice already exists
    existing_invoice = await crud.get_invoice_by_order(db, order_id=order_id)
    if existing_invoice:
        raise HTTPException(
            status_code=400,
            detail="Invoice already exists for this order",
        )
    return await services.create_invoice_service(
        db, order_id=order_id, invoice_number=invoice_number
    )


@router.post("/{order_id}/pay", response_model=schemas.Order)
async def process_payment(
    order_id: int,
    payment_reference: str,
    payment_method: str = "credit_card",
    db: AsyncSession = Depends(get_db)
):
    """
    Customer pays invoice.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.INVOICED:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not invoiced (current: {order.status})",
        )
    return await services.process_payment_service(
        db, order_id=order_id, payment_reference=payment_reference, payment_method=payment_method
    )


@router.post("/{order_id}/verify-payment", response_model=schemas.Order)
async def verify_payment(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Accountant verifies payment.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.PAID:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not paid (current: {order.status})",
        )
    return await services.verify_payment_service(
        db, order_id=order_id
    )


@router.post("/{order_id}/ship", response_model=schemas.Order)
async def ship_order(
    order_id: int,
    tracking_number: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Order staff ships the paid order.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.PAID:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not paid (current: {order.status})",
        )
    return await services.ship_order_service(
        db, order_id=order_id, tracking_number=tracking_number
    )


@router.post("/{order_id}/close", response_model=schemas.Order)
async def close_order(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Order staff closes the completed order.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != schemas.OrderStatusEnum.SHIPPED:
        raise HTTPException(
            status_code=400,
            detail=f"Order is not shipped (current: {order.status})",
        )
    return await services.close_order_service(
        db, order_id=order_id
    )