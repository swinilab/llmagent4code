import uuid
import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection_pool import get_session
# Import các SQLAlchemy models để phục vụ type hint và query DB
from app.models import Customer, Product, Order, LineItem, Payment, Invoice


# Helper to generate UUID v4 strings
def generate_uuid() -> str:
    return str(uuid.uuid4())


class CustomerRepository:
    @staticmethod
    async def create(session: AsyncSession, data) -> Customer:
        stmt = (
            insert(Customer)
            .values(
                id=generate_uuid(),
                name=data.name,
                address=data.address,
                phone=data.phone,
                banking_details={
                    "accountNumber": data.bankingDetails.accountNumber,
                    "bankName": data.bankingDetails.bankName,
                },
                role=data.role,
            )
            .returning(Customer)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @staticmethod
    async def get_by_id(session: AsyncSession, customer_id: str) -> Optional[Customer]:
        stmt = select(Customer).where(Customer.id == customer_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class ProductRepository:
    @staticmethod
    async def create(session: AsyncSession, data) -> Product:
        stmt = (
            insert(Product)
            .values(
                id=generate_uuid(),
                description=data.description,
                price_amount=data.price["amount"],  # Decimal from validator
                price_currency=data.price["currency"],
            )
            .returning(Product)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @staticmethod
    async def get_by_id(session: AsyncSession, product_id: str) -> Optional[Product]:
        stmt = select(Product).where(Product.id == product_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


class OrderRepository:
    @staticmethod
    async def create(session: AsyncSession, customer_id: str, line_items: List[dict]) -> Order:
        # Compute total amount and unit price snapshots using Decimal
        total = Decimal('0.00')
        item_objs = []
        for li in line_items:
            product = await ProductRepository.get_by_id(session, li["product_id"])
            if not product:
                raise ValueError('Product not found')
            unit_price: Decimal = product.price_amount
            total += unit_price * li["quantity"]
            item_objs.append({
                "product_id": product.id,
                "quantity": li["quantity"],
                "unit_price_snapshot": unit_price,
            })
        
        order_stmt = (
            insert(Order)
            .values(
                id=generate_uuid(),
                customer_id=customer_id,
                status='PLACED',
                total_amount=total,
            )
            .returning(Order)
        )
        result = await session.execute(order_stmt)
        order = result.scalar_one()

        # Insert line items
        for li in item_objs:
            await session.execute(
                insert(LineItem).values(
                    id=generate_uuid(),
                    order_id=order.id,
                    product_id=li["product_id"],
                    quantity=li["quantity"],
                    unit_price_snapshot=li["unit_price_snapshot"],
                )
            )
        await session.commit()
        return order

    @staticmethod
    async def get_by_id(session: AsyncSession, order_id: str) -> Optional[Order]:
        stmt = select(Order).where(Order.id == order_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(session: AsyncSession, order_id: str, new_status: str) -> None:
        stmt = update(Order).where(Order.id == order_id).values(status=new_status)
        await session.execute(stmt)
        await session.commit()


class PaymentRepository:
    @staticmethod
    async def create(session: AsyncSession, order_id: str, amount: Decimal, method: str) -> Payment:
        stmt = (
            insert(Payment)
            .values(
                id=generate_uuid(),
                order_id=order_id,
                amount=amount,
                method=method,
                status='PENDING',
            )
            .returning(Payment)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @staticmethod
    async def get_by_id(session: AsyncSession, payment_id: str) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(session: AsyncSession, payment_id: str, new_status: str) -> None:
        stmt = update(Payment).where(Payment.id == payment_id).values(status=new_status)
        await session.execute(stmt)
        await session.commit()


class InvoiceRepository:
    @staticmethod
    async def create(
        session: AsyncSession,
        order_id: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        issue_date: datetime.datetime,
        due_date: datetime.datetime,
    ) -> Invoice:
        stmt = (
            insert(Invoice)
            .values(
                id=generate_uuid(),
                order_id=order_id,
                billing_name=billing_name,
                billing_address=billing_address,
                total_amount=total_amount,
                issue_date=issue_date,
                due_date=due_date,
                status='ISSUED',
            )
            .returning(Invoice)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @staticmethod
    async def get_by_id(session: AsyncSession, invoice_id: str) -> Optional[Invoice]:
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()