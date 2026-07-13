from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import order as crud_order
from app.db.models import Order
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderStatus
from app.schemas.invoice import InvoiceCreate, InvoiceStatus
from app.schemas.payment import PaymentCreate, PaymentStatus, PaymentMethod
from sqlalchemy import select
from sqlalchemy.orm import selectinload
async def get_order(db: AsyncSession, order_id: int) -> Optional[OrderResponse]:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    obj = result.scalar_one_or_none()
    return OrderResponse.from_orm(obj) if obj else None

async def get_orders(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[OrderResponse]:
    result = await db.execute(
        select(Order)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Order.items))
    )
    objs = result.scalars().all()
    return [OrderResponse.from_orm(obj) for obj in objs]

async def create_order_with_items(
    db: AsyncSession, order_in: OrderCreate
) -> OrderResponse:
    # Create order
    order_data = order_in.dict(exclude={"items"})
    db_order = Order(**order_data)
    db.add(db_order)
    await db.flush()  # get id
    # Create items
    total = 0
    for item_in in order_in.items:
        item_data = item_in.dict()
        item = OrderItem(**item_data, order_id=db_order.id)
        db.add(item)
        total += item_data["quantity"] * item_data["unit_price"]
    db_order.total_amount = total
    await db.commit()
    await db.refresh(db_order)
    # reload with items
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Order)
        .where(Order.id == db_order.id)
        .options(selectinload(Order.items))
    )
    order_with_items = result.scalar_one()
    return OrderResponse.from_orm(order_with_items)

async def update_order_status(
    db: AsyncSession, order_id: int, status: OrderStatus
) -> Optional[OrderResponse]:
    obj = await crud_order.get_order(db, order_id)
    if not obj:
        return None
    updated = await crud_order.update_order(db, obj, OrderUpdate(status=status))
    await db.commit()
    return await get_order(db, order_id)
async def delete_order(db: AsyncSession, order_id: int) -> bool:
    obj = await crud_order.get_order(db, order_id)
    if not obj:
        return False
    await crud_order.delete_order(db, order_id)
    return True
async def process_order_workflow(
    db: AsyncSession, order_id: int
) -> dict:
    """
    Simulate workflow: staff accepts, accountant invoices, customer pays, accountant verifies, staff ships, staff closes.
    In reality, each step would be triggered by different role endpoints.
    This service just demonstrates the sequence.
    """
    # 1. staff accepts
    await update_order_status(db, order_id, OrderStatus.accepted)
    # 2. accountant creates invoice (simplified)
    order = await get_order(db, order_id)
    if not order:
        return {"error": "Order not found"}
    # create invoice
    from app.services import invoice_service, payment_service
    invoice_in = InvoiceCreate(
        order_id=order.id,
        billing_info="Customer billing info",
        amount=order.total_amount,
        status=InvoiceStatus.issued
    )
    await invoice_service.create_invoice(db, invoice_in)
    # 3. customer pays (simulate payment)
    payment_in = PaymentCreate(
        order_id=order.id,
        amount=order.total_amount,
        method=PaymentMethod.credit_card,
        status=PaymentStatus.completed
    )
    await payment_service.create_payment(db, payment_in)
    # 4. accountant verifies payment (already completed)
    # 5. staff ships
    await update_order_status(db, order_id, OrderStatus.shipped)
    # 6. staff closes
    await update_order_status(db, order_id, OrderStatus.closed)
    return {"status": "completed"}