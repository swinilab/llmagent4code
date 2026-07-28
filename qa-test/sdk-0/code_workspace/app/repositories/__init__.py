"""Repository layer – async SQLAlchemy operations"""
from typing import List, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.orm import Customer, Product, Order, Invoice, Payment
from app.models.schemas import OrderCreate, LineItem
from decimal import Decimal
import uuid

class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data) -> Customer:
        obj = Customer(**data.dict())
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get(self, customer_id: str) -> Optional[Customer]:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        return result.scalar_one_or_none()

class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data) -> Product:
        obj = Product(**data.dict())
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get(self, product_id: str) -> Optional[Product]:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, order_data: OrderCreate) -> Order:
        # Resolve product prices snapshot
        line_items = []
        total = Decimal('0.00')
        for item in order_data.lineItems:
            prod = await self.db.execute(select(Product).where(Product.id == item.productRef))
            product = prod.scalar_one_or_none()
            if not product:
                raise ValueError(f"Product {item.productRef} not found")
            unit_price = product.price_amount
            line_items.append({
                "productRef": item.productRef,
                "quantity": item.quantity,
                "unitPriceSnapshot": str(unit_price)
            })
            total += unit_price * item.quantity
        order_dict = {
            "customer_id": order_data.customerRef,
            "line_items": line_items,
            "total_amount": total,
            "status": "PLACED",
        }
        order = Order(**order_dict)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get(self, order_id: str) -> Optional[Order]:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_status(self, order_id: str, new_status: str) -> None:
        await self.db.execute(update(Order).where(Order.id == order_id).values(status=new_status))
        await self.db.commit()

class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data) -> Invoice:
        obj = Invoice(**data.dict())
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get(self, invoice_id: str) -> Optional[Invoice]:
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalar_one_or_none()

class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data) -> Payment:
        obj = Payment(**data.dict())
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get(self, payment_id: str) -> Optional[Payment]:
        result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()
