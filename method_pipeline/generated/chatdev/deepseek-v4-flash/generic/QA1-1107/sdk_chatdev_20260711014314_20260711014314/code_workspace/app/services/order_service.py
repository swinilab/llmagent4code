"""
Service layer for Order entity.
Handles order lifecycle, line item calculations, and status transitions.
"""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.enums import OrderStatus
from app.models.order import Order, OrderLineItem
from app.schemas.order import OrderCreate, OrderUpdate, OrderLineItemCreate


# Valid status transitions for the order workflow
VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.REVIEW, OrderStatus.CANCELLED],
    OrderStatus.REVIEW: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.INVOICED, OrderStatus.CANCELLED],
    OrderStatus.INVOICED: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [OrderStatus.CLOSED],
    OrderStatus.CLOSED: [],
    OrderStatus.CANCELLED: [],
}

# Terminal states where no modifications are allowed
TERMINAL_STATES = {OrderStatus.CLOSED, OrderStatus.CANCELLED}

TAX_RATE = Decimal(settings.tax_rate)
SHIPPING_COST = Decimal(settings.shipping_cost)


class OrderService:
    """Business logic for order operations."""

    @staticmethod
    def _calculate_totals(line_items: List[OrderLineItemCreate]) -> tuple:
        """Calculate subtotal, tax, shipping, and total from line items."""
        subtotal = sum(
            Decimal(str(item.unit_price)) * Decimal(str(item.quantity))
            for item in line_items
        )
        tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
        shipping = SHIPPING_COST
        total = (subtotal + tax_amount + shipping).quantize(Decimal("0.01"))
        return subtotal.quantize(Decimal("0.01")), tax_amount, shipping, total

    @staticmethod
    async def create(db: AsyncSession, data: OrderCreate) -> Order:
        """Create a new order with line items and calculated totals."""
        subtotal, tax_amount, shipping_cost, total_amount = OrderService._calculate_totals(data.line_items)

        order = Order(
            customer_id=data.customer_id,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            notes=data.notes,
        )
        db.add(order)
        await db.flush()

        for item_data in data.line_items:
            line_total = (Decimal(str(item_data.unit_price)) * Decimal(str(item_data.quantity))).quantize(Decimal("0.01"))
            line_item = OrderLineItem(
                order_id=order.id,
                product_id=item_data.product_id,
                product_description=item_data.product_description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                currency=item_data.currency,
                line_total=line_total,
            )
            db.add(line_item)

        await db.flush()
        # Refresh to load all server-side defaults (created_at, updated_at) and relationships
        await db.refresh(order)
        return order

    @staticmethod
    async def get_by_id(db: AsyncSession, order_id: str) -> Optional[Order]:
        """Retrieve an order by ID with line items eagerly loaded."""
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        customer_id: Optional[str] = None,
    ) -> List[Order]:
        """List orders with optional filters and pagination."""
        stmt = select(Order).options(selectinload(Order.line_items))
        if status:
            stmt = stmt.where(Order.status == status)
        if customer_id:
            stmt = stmt.where(Order.customer_id == customer_id)
        stmt = stmt.offset(skip).limit(limit).order_by(Order.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_status(db: AsyncSession, order_id: str, new_status: OrderStatus) -> Optional[Order]:
        """Transition an order to a new status with validation."""
        order = await OrderService.get_by_id(db, order_id)
        if not order:
            return None

        allowed = VALID_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from {order.status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )

        order.status = new_status
        await db.flush()
        # Refresh to load server-side defaults (updated_at) and ensure all attributes are available
        await db.refresh(order)
        return order

    @staticmethod
    async def update(db: AsyncSession, order_id: str, data: OrderUpdate) -> Optional[Order]:
        """Update order fields (notes, invoice_ref, or status).

        Guards against modifying any field on orders in terminal states (CLOSED, CANCELLED),
        since those are terminal states where data should be immutable.
        """
        order = await OrderService.get_by_id(db, order_id)
        if not order:
            return None

        # Guard: do not allow any modifications on terminal-state orders
        if order.status in TERMINAL_STATES:
            raise ValueError(
                f"Cannot update order {order_id} in terminal status "
                f"{order.status.value}. Terminal orders are immutable."
            )

        update_data = data.model_dump(exclude_unset=True)
        status = update_data.pop("status", None)
        if status:
            order = await OrderService.update_status(db, order_id, status)
            if not order:
                return None

        for field, value in update_data.items():
            setattr(order, field, value)

        await db.flush()
        await db.refresh(order)
        return order

    @staticmethod
    async def delete(db: AsyncSession, order_id: str) -> bool:
        """Delete an order by ID."""
        order = await OrderService.get_by_id(db, order_id)
        if not order:
            return False
        await db.delete(order)
        await db.flush()
        return True
