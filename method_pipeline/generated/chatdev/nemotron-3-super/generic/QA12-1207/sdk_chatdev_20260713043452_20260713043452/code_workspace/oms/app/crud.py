from typing import List, Optional, Union, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app import models, schemas
from datetime import datetime, timezone
# Customer CRUD
async def get_customer(db: AsyncSession, customer_id: int) -> Optional[models.Customer]:
    result = await db.execute(select(models.Customer).where(models.Customer.id == customer_id))
    return result.scalar_one_or_none()


async def get_customer_by_email(db: AsyncSession, email: str) -> Optional[models.Customer]:
    result = await db.execute(select(models.Customer).where(models.Customer.email == email))
    return result.scalar_one_or_none()


async def get_customers(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.Customer]:
    result = await db.execute(select(models.Customer).offset(skip).limit(limit))
    return result.scalars().all()


async def create_customer(db: AsyncSession, *, customer_in: schemas.CustomerCreate) -> models.Customer:
    customer = models.Customer(
        name=customer_in.name,
        email=customer_in.email,
        phone=customer_in.phone,
        address=customer_in.address,
        is_active=customer_in.is_active,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def update_customer(
    db: AsyncSession, *, customer_id: int, customer_in: Union[schemas.CustomerUpdate, Dict[str, Any]]
) -> Optional[models.Customer]:
    customer = await get_customer(db, customer_id=customer_id)
    if not customer:
        return None
    update_data = customer_in if isinstance(customer_in, dict) else customer_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def delete_customer(db: AsyncSession, *, customer_id: int) -> Optional[models.Customer]:
    customer = await get_customer(db, customer_id=customer_id)
    if not customer:
        return None
    await db.delete(customer)
    await db.commit()
    return customer


# Product CRUD
async def get_product(db: AsyncSession, product_id: int) -> Optional[models.Product]:
    result = await db.execute(select(models.Product).where(models.Product.id == product_id))
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str) -> Optional[models.Product]:
    result = await db.execute(select(models.Product).where(models.Product.sku == sku))
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.Product]:
    result = await db.execute(select(models.Product).offset(skip).limit(limit))
    return result.scalars().all()


async def create_product(db: AsyncSession, *, product_in: schemas.ProductCreate) -> models.Product:
    product = models.Product(
        name=product_in.name,
        description=product_in.description,
        price=product_in.price,
        sku=product_in.sku,
        is_active=product_in.is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, *, product_id: int, product_in: Union[schemas.ProductUpdate, Dict[str, Any]]
) -> Optional[models.Product]:
    product = await get_product(db, product_id=product_id)
    if not product:
        return None
    update_data = product_in if isinstance(product_in, dict) else product_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, *, product_id: int) -> Optional[models.Product]:
    product = await get_product(db, product_id=product_id)
    if not product:
        return None
    await db.delete(product)
    await db.commit()
    return product


# Order CRUD
async def get_order(db: AsyncSession, order_id: int) -> Optional[models.Order]:
    result = await db.execute(select(models.Order).where(models.Order.id == order_id))
    return result.scalar_one_or_none()


async def get_order_by_number(db: AsyncSession, order_number: str) -> Optional[models.Order]:
    result = await db.execute(select(models.Order).where(models.Order.order_number == order_number))
    return result.scalar_one_or_none()


async def get_orders(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.Order]:
    result = await db.execute(select(models.Order).offset(skip).limit(limit))
    return result.scalars().all()


async def create_order(db: AsyncSession, *, order_in: schemas.OrderCreate) -> models.Order:
    # Create order without items first
    order_data = order_in.dict(exclude={"order_items"})
    order = models.Order(**order_data)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Now create order items if any
    for item_in in getattr(order_in, "order_items", []):
        await create_order_item(
            db, order_item_in=item_in, order_id=order.id, commit=False
        )

    # Recalculate total
    await update_order_total(db, order_id=order.id, commit=False)
    await db.commit()
    await db.refresh(order)
    return order


async def update_order(
    db: AsyncSession, *, order_id: int, order_in: Union[schemas.OrderUpdate, Dict[str, Any]]
) -> Optional[models.Order]:
    order = await get_order(db, order_id=order_id)
    if not order:
        return None
    update_data = order_in if isinstance(order_in, dict) else order_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(db: AsyncSession, *, order_id: int) -> Optional[models.Order]:
    order = await get_order(db, order_id=order_id)
    if not order:
        return None
    await db.delete(order)
    await db.commit()
    return order


# OrderItem CRUD
async def get_order_item(db: AsyncSession, order_item_id: int) -> Optional[models.OrderItem]:
    result = await db.execute(select(models.OrderItem).where(models.OrderItem.id == order_item_id))
    return result.scalar_one_or_none()


async def get_order_items_by_order(db: AsyncSession, order_id: int) -> List[models.OrderItem]:
    result = await db.execute(select(models.OrderItem).where(models.OrderItem.order_id == order_id))
    return result.scalars().all()


async def create_order_item(
    db: AsyncSession, *, order_item_in: schemas.OrderItemCreate, order_id: int, commit: bool = True
) -> models.OrderItem:
    order_item = models.OrderItem(
        product_id=order_item_in.product_id,
        quantity=order_item_in.quantity,
        unit_price=order_item_in.unit_price,
        total_price=order_item_in.total_price,
        order_id=order_id,
    )
    db.add(order_item)
    if commit:
        await db.commit()
        await db.refresh(order_item)
    else:
        await db.flush()
        await db.refresh(order_item)
    return order_item


async def update_order_item(
    db: AsyncSession, *, order_item_id: int, order_item_in: Union[schemas.OrderItemUpdate, Dict[str, Any]]
) -> Optional[models.OrderItem]:
    order_item = await get_order_item(db, order_item_id=order_item_id)
    if not order_item:
        return None
    update_data = order_item_in if isinstance(order_item_in, dict) else order_item_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order_item, field, value)
    db.add(order_item)
    await db.commit()
    await db.refresh(order_item)
    return order_item


async def delete_order_item(db: AsyncSession, *, order_item_id: int) -> Optional[models.OrderItem]:
    order_item = await get_order_item(db, order_item_id=order_item_id)
    if not order_item:
        return None
    await db.delete(order_item)
    await db.commit()
    return order_item


# Invoice CRUD
async def get_invoice(db: AsyncSession, invoice_id: int) -> Optional[models.Invoice]:
    result = await db.execute(select(models.Invoice).where(models.Invoice.id == invoice_id))
    return result.scalar_one_or_none()


async def get_invoice_by_number(db: AsyncSession, invoice_number: str) -> Optional[models.Invoice]:
    result = await db.execute(select(models.Invoice).where(models.Invoice.invoice_number == invoice_number))
    return result.scalar_one_or_none()


async def get_invoice_by_order(db: AsyncSession, order_id: int) -> Optional[models.Invoice]:
    result = await db.execute(select(models.Invoice).where(models.Invoice.order_id == order_id))
    return result.scalar_one_or_none()


async def get_invoices(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.Invoice]:
    result = await db.execute(select(models.Invoice).offset(skip).limit(limit))
    return result.scalars().all()


async def create_invoice(db: AsyncSession, *, invoice_in: schemas.InvoiceCreate) -> models.Invoice:
    invoice = models.Invoice(**invoice_in.dict())
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def update_invoice(
    db: AsyncSession, *, invoice_id: int, invoice_in: Union[schemas.InvoiceUpdate, Dict[str, Any]]
) -> Optional[models.Invoice]:
    invoice = await get_invoice(db, invoice_id=invoice_id)
    if not invoice:
        return None
    update_data = invoice_in if isinstance(invoice_in, dict) else invoice_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def delete_invoice(db: AsyncSession, *, invoice_id: int) -> Optional[models.Invoice]:
    invoice = await get_invoice(db, invoice_id=invoice_id)
    if not invoice:
        return None
    await db.delete(invoice)
    await db.commit()
    return invoice


# Payment CRUD
async def get_payment(db: AsyncSession, payment_id: int) -> Optional[models.Payment]:
    result = await db.execute(select(models.Payment).where(models.Payment.id == payment_id))
    return result.scalar_one_or_none()


async def get_payment_by_transaction(db: AsyncSession, transaction_id: str) -> Optional[models.Payment]:
    result = await db.execute(select(models.Payment).where(models.Payment.transaction_id == transaction_id))
    return result.scalar_one_or_none()


async def get_payment_by_order(db: AsyncSession, order_id: int) -> Optional[models.Payment]:
    result = await db.execute(select(models.Payment).where(models.Payment.order_id == order_id))
    return result.scalar_one_or_none()


async def get_payments(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[models.Payment]:
    result = await db.execute(select(models.Payment).offset(skip).limit(limit))
    return result.scalars().all()


async def create_payment(db: AsyncSession, *, payment_in: schemas.PaymentCreate) -> models.Payment:
    payment_data = payment_in.dict()
    # Get order to obtain customer_id
    order = await get_order(db, order_id=payment_in.order_id)
    if not order:
        raise ValueError(f"Order {payment_in.order_id} not found")
    payment_data["customer_id"] = order.customer_id
    payment_data["processed_at"] = func.now()
    payment_data["processed_at"] = datetime.now(timezone.utc)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def update_payment(
    db: AsyncSession, *, payment_id: int, payment_in: Union[schemas.PaymentUpdate, Dict[str, Any]]
) -> Optional[models.Payment]:
    payment = await get_payment(db, payment_id=payment_id)
    if not payment:
        return None
    update_data = payment_in if isinstance(payment_in, dict) else payment_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def delete_payment(db: AsyncSession, *, payment_id: int) -> Optional[models.Payment]:
    payment = await get_payment(db, payment_id=payment_id)
    if not payment:
        return None
    await db.delete(payment)
    await db.commit()
    return payment


# Helper functions
async def update_order_total(db: AsyncSession, *, order_id: int, commit: bool = True) -> None:
    \"\"\"Recalculate and update the total amount of an order based on its items.\"\"\"
    result = await db.execute(
        select(models.OrderItem).where(models.OrderItem.order_id == order_id)
    )
    items = result.scalars().all()
    total = sum(item.quantity * item.unit_price for item in items)
    await db.execute(
        update(models.Order)
        .where(models.Order.id == order_id)
        .values(total_amount=total)
    )
    if commit:
        await db.commit()
    else:
        await db.flush()