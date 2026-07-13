from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from oms_backend.app.models.order import Order, OrderStatus
from oms_backend.app.models.order_item import OrderItem
from oms_backend.app.models.product import Product
from oms_backend.app.models.invoice import Invoice, InvoiceStatus
from oms_backend.app.models.payment import Payment, PaymentStatus, PaymentMethod
from oms_backend.app.schemas.order import OrderCreate, OrderUpdate
from oms_backend.app.schemas.order_item import OrderItemCreate
from oms_backend.app.schemas.invoice import InvoiceCreate
from oms_backend.app.schemas.payment import PaymentCreate


def create_order(db: Session, order: OrderCreate):
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def update_order(db: Session, order_id: int, order: OrderUpdate):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        update_data = order.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_order, field, value)
        db.commit()
        db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: int):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        db.delete(db_order)
        db.commit()
def delete_order(db: Session, order_id: int):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if db_order:
        db.delete(db_order)
        db.commit()
    return db_order


def accept_order(db: Session, order_id: int):
    """
    Order staff accepts an order (PENDING -> ACCEPTED)
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None
    if db_order.status != OrderStatus.PENDING:
        raise ValueError(f"Order {order_id} is not in PENDING status. Current status: {db_order.status}")
    
    db_order.status = OrderStatus.ACCEPTED
    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)
    return db_order


def create_invoice_for_order(db: Session, order_id: int, billing_info: str):
    """
    Accountant creates an invoice for an accepted order (ACCEPTED -> INVOICED)
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None
    if db_order.status != OrderStatus.ACCEPTED:
        raise ValueError(f"Order {order_id} is not in ACCEPTED status. Current status: {db_order.status}")
    
    # Create invoice
    invoice_data = InvoiceCreate(
        order_id=order_id,
        billing_info=billing_info,
        status=InvoiceStatus.DRAFT  # Start as draft, will be set to ISSUED when finalized
    )
    db_invoice = Invoice(**invoice_data.dict())
    db.add(db_invoice)
    db.flush()  # Get the ID without committing yet
    
    # Update order with invoice ID and status
    db_order.invoice_id = db_invoice.id
    db_order.status = OrderStatus.INVOICED
    db_order.updated_at = datetime.utcnow()
    
    # Calculate tax and update invoice totals
    # For simplicity, we'll use a 10% tax rate
    tax_rate = 0.10
    subtotal = db_order.total_amount
    tax_amount = subtotal * tax_rate
    total_amount = subtotal + tax_amount
    
    db_invoice.subtotal = subtotal
    db_invoice.tax_amount = tax_amount
    db_invoice.total_amount = total_amount
    db_invoice.status = InvoiceStatus.ISSUED
    db_invoice.issue_date = datetime.utcnow()
    # Due date is 30 days from issue date
    db_invoice.due_date = datetime.utcnow().replace(day=datetime.utcnow().day + 30)
    
    db.commit()
    db.refresh(db_order)
    db.refresh(db_invoice)
    return db_invoice


def process_payment_for_order(db: Session, order_id: int, payment_method: PaymentMethod, amount: float = None):
    """
    Customer pays for an invoice (INVOICED -> PAID)
    This creates a payment record and processes it
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None
    if db_order.status != OrderStatus.INVOICED:
        raise ValueError(f"Order {order_id} is not in INVOICED status. Current status: {db_order.status}")
    
    # If amount not specified, use order total
    if amount is None:
        amount = db_order.total_amount
    
    # Create payment record
    payment_data = PaymentCreate(
        order_id=order_id,
        amount=amount,
        payment_method=payment_method,
        status=PaymentStatus.PROCESSING
    )
    db_payment = Payment(**payment_data.dict())
    db.add(db_payment)
    db.flush()  # Get the ID
    
    # In a real system, we would integrate with a payment gateway here
    # For this exercise, we'll simulate immediate payment processing
    # In production, this would be handled asynchronously via Celery
    
    # Update payment status to completed
    db_payment.status = PaymentStatus.COMPLETED
    db_payment.updated_at = datetime.utcnow()
    
    # Update order status to paid
    db_order.status = OrderStatus.PAID
    db_order.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_payment)
    db.refresh(db_order)
    return db_payment


def verify_payment(db: Session, payment_id: int):
    """
    Accountant verifies a payment has been processed successfully
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        return None
    
    # In a real system, this might involve checking with the payment gateway
    # For this exercise, we'll assume if it's COMPLETED, it's verified
    if db_payment.status == PaymentStatus.COMPLETED:
        return db_payment
    else:
        raise ValueError(f"Payment {payment_id} is not completed. Current status: {db_payment.status}")


def ship_order(db: Session, order_id: int):
    """
    Order staff ships a paid order (PAID -> SHIPPED)
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None
    if db_order.status != OrderStatus.PAID:
        raise ValueError(f"Order {order_id} is not in PAID status. Current status: {db_order.status}")
    
    db_order.status = OrderStatus.SHIPPED
    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)
    return db_order


def close_order(db: Session, order_id: int):
    """
    Order staff closes a shipped order (SHIPPED -> CLOSED)
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        return None
    if db_order.status != OrderStatus.SHIPPED:
        raise ValueError(f"Order {order_id} is not in SHIPPED status. Current status: {db_order.status}")
    
    db_order.status = OrderStatus.CLOSED
    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)
    return db_order


def add_order_item(db: Session, order_id: int, item: OrderItemCreate):
    return db_order


def add_order_item(db: Session, order_id: int, item: OrderItemCreate):
    # get product price
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
        return None
    total_price = product.base_price * item.quantity
    db_item = OrderItem(
        order_id=order_id,
        product_id=item.product_id,
        quantity=item.quantity,
        unit_price=product.base_price,
        total_price=total_price
    )
    db.add(db_item)
    # update order total
    order = db.query(Order).filter(Order.id == order_id).first()
    if order:
        order.total_amount += total_price
        db.commit()
        db.refresh(db_item)
        db.refresh(order)
    return db_item


def remove_order_item(db: Session, order_item_id: int):
    db_item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
    if db_item:
        order = db.query(Order).filter(Order.id == db_item.order_id).first()
        if order:
            order.total_amount -= db_item.total_price
            db.delete(db_item)
            db.commit()
            db.refresh(order)
        else:
            db.delete(db_item)
            db.commit()
    return db_item


def create_order_with_items(db: Session, order: OrderCreate, items: List[OrderItemCreate]):
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    total_amount = 0.0
    for item in items:
        db_item = add_order_item(db, db_order.id, item)
        if db_item is None:
            # If product not found, rollback order creation
            db.delete(db_order)
            db.commit()
            return None
        total_amount += db_item.total_price
    # Update order total (already updated in add_order_item, but we set again for consistency)
    db_order.total_amount = total_amount
    db.commit()
    db.refresh(db_order)
    return db_order