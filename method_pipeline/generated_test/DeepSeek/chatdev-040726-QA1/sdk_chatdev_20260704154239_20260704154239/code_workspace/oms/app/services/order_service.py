"""
Service layer for Order operations.
"""
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderCreate, OrderStatusUpdate


class OrderStateError(Exception):
    """Raised when an invalid order state transition is attempted."""


class OrderService:
    """Business logic for managing orders."""

    # Valid transitions for direct status updates (non-workflow paths)
    # WorkflowService enforces the full lifecycle; this is a safety net.
    VALID_DIRECT_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
        OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CLOSED},
        OrderStatus.ACCEPTED: {OrderStatus.INVOICED, OrderStatus.CLOSED},
        OrderStatus.INVOICED: {OrderStatus.PAID, OrderStatus.CLOSED},
        OrderStatus.PAID: {OrderStatus.VERIFIED, OrderStatus.CLOSED},
        OrderStatus.VERIFIED: {OrderStatus.SHIPPED, OrderStatus.CLOSED},
        OrderStatus.SHIPPED: {OrderStatus.CLOSED},
        OrderStatus.CLOSED: set(),
    }

    @staticmethod
    def create(db: Session, data: OrderCreate, commit: bool = True) -> Order:
        total = sum(item.unit_price * item.quantity for item in data.line_items)
        order = Order(
            customer_id=data.customer_id,
            currency=data.currency,
            total_amount=total,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.flush()
        for item in data.line_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
            )
            db.add(order_item)
        if commit:
            db.commit()
            db.refresh(order)
        else:
            db.flush()
        return order

    @staticmethod
    def get_by_id(db: Session, order_id: str) -> Order | None:
        return (
            db.query(Order)
            .options(joinedload(Order.line_items))
            .filter(Order.id == order_id)
            .first()
        )

    @staticmethod
    def list_by_customer(db: Session, customer_id: str, skip: int = 0, limit: int = 100) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.line_items))
            .filter(Order.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Order]:
        return (
            db.query(Order)
            .options(joinedload(Order.line_items))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_status(
        db: Session,
        order_id: str,
        data: OrderStatusUpdate,
        commit: bool = True,
        skip_validation: bool = False,
    ) -> Order | None:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            return None
        if not skip_validation:
            allowed = OrderService.VALID_DIRECT_TRANSITIONS.get(order.status, set())
            if data.status not in allowed:
                raise OrderStateError(
                    f"Cannot transition from {order.status.value} to {data.status.value}. "
                    f"Allowed targets: {[s.value for s in allowed] or 'none'}"
                )
        order.status = data.status
        if commit:
            db.commit()
            db.refresh(order)
        else:
            db.flush()
        return order

    @staticmethod
    def delete(db: Session, order_id: str, commit: bool = True) -> bool:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            return False
        db.delete(order)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
