from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app import crud, models, schemas
from app.models import OrderStatusEnum
import logging
from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone
logger = logging.getLogger(__name__)


# Order status constants (using enum)
ORDER_STATUS_PENDING = OrderStatusEnum.PENDING
ORDER_STATUS_ACCEPTED = OrderStatusEnum.ACCEPTED
ORDER_STATUS_INVOICED = OrderStatusEnum.INVOICED
ORDER_STATUS_PAID = OrderStatusEnum.PAID
ORDER_STATUS_SHIPPED = OrderStatusEnum.SHIPPED
ORDER_STATUS_CLOSED = OrderStatusEnum.CLOSED
ORDER_STATUS_CANCELLED = OrderStatusEnum.CANCELLED


async def create_order_service(
    db: AsyncSession, *, customer_id: int, order_number: str, notes: Optional[str] = None
) -> models.Order:
    """
    Service for customer placing an order.
    Creates an order with status 'pending' and no items.
    """
    order_in = schemas.OrderCreate(
        customer_id=customer_id,
        order_number=order_number,
        total_amount=0.0,
        notes=notes,
        is_active=True,
        order_items=[],
    )
    order = await crud.create_order(db, order=order_in)
    logger.info(f"Order {order.id} created for customer {customer_id}")
    return order


async def add_item_to_order(
    db: AsyncSession, *, order_id: int, product_id: int, quantity: int
) -> models.OrderItem:
    """
    Add a product to an order. Recalculate order total.
    """
    # Get product for price
    product = await crud.get_product(db, product_id=product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")
    if not product.is_active:
        raise ValueError(f"Product {product_id} is not active")
    
    unit_price = product.price
    total_price = unit_price * quantity
    
    # Create order item
    order_item_in = schemas.OrderItemCreate(
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
    )
    order_item = await crud.create_order_item(
        db, order_item_in=order_item_in, order_id=order_id
    )
    
    # Recalculate order total
    await crud.update_order_total(db, order_id=order_id)
    
    logger.info(f"Added product {product_id} to order {order_id}")
    return order_item


async def review_order_service(
    db: AsyncSession, *, order_id: int, notes: Optional[str] = None
) -> models.Order:
    """
    Order staff reviews and accepts the order.
    Changes status from pending to accepted.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_PENDING:
        raise ValueError(f"Order {order_id} is not in pending status")
    
    order.status = ORDER_STATUS_ACCEPTED
    if notes:
        order.notes = notes
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(f"Order {order_id} accepted by staff")
    return order


async def create_invoice_service(
    db: AsyncSession, *, order_id: int, invoice_number: str
) -> models.Order:
    """
    Accountant creates invoice for accepted order.
    Changes status from accepted to invoiced.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_ACCEPTED:
        raise ValueError(f"Order {order_id} is not accepted yet")
    
    # Update order status
    order.status = ORDER_STATUS_INVOICED
    
    # Create invoice record
    invoice_in = schemas.InvoiceCreate(
        order_id=order.id,
        invoice_number=invoice_number,
        billing_info=f"Customer: {order.customer.name if order.customer else 'Unknown'}",
        due_date=order.created_at + timedelta(days=30),
    )
    invoice = await crud.create_invoice(db, invoice_in=invoice_in)
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(f"Invoice {invoice_number} created for order {order_id}")
    return order


async def process_payment_service(
    db: AsyncSession, *, order_id: int, payment_reference: str, payment_method: str = "credit_card"
) -> models.Order:
    """
    Customer pays invoice (simulated).
    Changes status from invoiced to paid.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_INVOICED:
        raise ValueError(f"Order {order_id} is not invoiced yet")
    
    # Update order status
    order.status = ORDER_STATUS_PAID
    
    # Create payment record
    payment_in = schemas.PaymentCreate(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payment_method,
        transaction_id=payment_reference,
        status="processed",
    )
    payment = await crud.create_payment(db, payment_in=payment_in)
    
    # Update invoice status to paid
    invoice = await crud.get_invoice_by_order(db, order_id=order_id)
    if invoice:
        invoice.status = "paid"
        db.add(invoice)
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(f"Payment processed for order {order_id}")
    return order


async def verify_payment_service(
    db: AsyncSession, *, order_id: int
) -> models.Order:
    """
    Accountant verifies payment.
    In our flow, payment processing already set status to paid.
    Verification could be checking payment record is verified.
    We'll mark payment as verified and optionally update order status to shipped? 
    But per workflow, after payment verification, order staff ships.
    We'll just verify payment and leave order as paid.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_PAID:
        raise ValueError(f"Order {order_id} is not paid yet")
    
    # Update payment status to verified
    payment = await crud.get_payment_by_order(db, order_id=order_id)
    if payment:
        payment.status = "verified"
        payment.verified_at = datetime.now(timezone.utc)
        db.add(payment)
    
    await db.commit()
    await db.refresh(order)
    logger.info(f"Payment verified for order {order_id}")
    return order


async def ship_order_service(
    db: AsyncSession, *, order_id: int, tracking_number: Optional[str] = None
) -> models.Order:
    """
    Order staff ships paid order.
    Changes status from paid to shipped.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_PAID:
        raise ValueError(f"Order {order_id} is not paid yet")
    
    order.status = ORDER_STATUS_SHIPPED
    if tracking_number:
        # We could add a shipments table, but for simplicity add to notes
        if order.notes:
            order.notes += f"\nTracking: {tracking_number}"
        else:
            order.notes = f"Tracking: {tracking_number}"
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(f"Order {order_id} shipped")
    return order


async def close_order_service(
    db: AsyncSession, *, order_id: int
) -> models.Order:
    """
    Order staff closes completed order.
    Changes status from shipped to closed.
    """
    order = await crud.get_order(db, order_id=order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    if order.status != ORDER_STATUS_SHIPPED:
        raise ValueError(f"Order {order_id} is not shipped yet")
    
    order.status = ORDER_STATUS_CLOSED
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(f"Order {order_id} closed")
    return order


# Additional helper services
async def get_order_with_details(db: AsyncSession, order_id: int) -> Optional[models.Order]:
    """Get order with customer, items, invoices, payments."""
    result = await db.execute(
        select(models.Order)
        .where(models.Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    return order