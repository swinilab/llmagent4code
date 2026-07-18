"""
Order service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.order import OrderRepository
from app.repositories.order_line_item import OrderLineItemRepository
from app.models.order import OrderStatus, Order
from app.schemas.order import OrderCreate, OrderRead
import uuid
import structlog
Order service layer.
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.order import OrderRepository
from app.repositories.order_line_item import OrderLineItemRepository
from app.models.order import OrderStatus, Order
from app.schemas.order import OrderCreate, OrderRead
import structlog

logger = structlog.get_logger(__name__)


class OrderService:
    """Order service."""

    def __init__(self, db: Session):
    def __init__(self, db: Session):
        self.order_repo = OrderRepository(db)
        self.line_item_repo = OrderLineItemRepository(db)
        self.db = db

    def create_order(self, order: OrderCreate) -> OrderRead:
        """Create a new order and log to outbox in a single transaction."""
        try:
            # Create order (but do not commit yet)
            db_order = self.order_repo.create(order)
    def create_order(self, order: OrderCreate) -> OrderRead:
        """Create a new order and log to outbox in a single transaction."""
        try:
            # Create order (but do not commit yet)
            db_order = self.order_repo.create(order)
            db_order.is_pending_recovery = True  # Mark for recovery

            # Add line items
            for line_item in order.line_items:
                self.line_item_repo.create(line_item, db_order.id)

            # Log to outbox (same transaction)
            from app.models.outbox.outbox import Outbox
            outbox_event = Outbox(
                id=str(uuid.uuid4()),
                event_type="ORDER_PLACED",
                payload={"order_id": db_order.id},
                processed=False
            )
            self.db.add(outbox_event)
            
            # Log to recovery log
            from app.models.recovery_log import RecoveryLog
            recovery_log = RecoveryLog(
                id=str(uuid.uuid4()),
                aggregate_type="ORDER",
                aggregate_id=db_order.id,
                status="PENDING_ACCEPTANCE",
                checkpoint_data={"order_data": order.dict()}
            )
            self.db.add(recovery_log)
            
            self.db.commit()  # Commit both order, outbox, and recovery log
            return OrderRead.from_orm(db_order)
        except Exception as e:
            self.db.rollback()
            self.logger.error("Failed to create order", error=str(e))
            raise
            from app.models.outbox.outbox import Outbox
            outbox_event = Outbox(
                event_type="ORDER_PLACED",
                payload={"order_id": db_order.id},
                processed=False
            )
            self.db.add(outbox_event)
            self.db.commit()  # Commit both order and outbox

            return OrderRead.model_validate(db_order)
            payload={"order_id": db_order.id}
        )
        self.db.add(outbox_event)
        self.db.commit()  # Ensure immediate persistence
        
        process_order_workflow.delay(db_order.id, "created")
        return self.get_order(db_order.id)
        return OrderRead.model_validate(db_order)

    def update_order_status(self, order_id: int, status: OrderStatus) -> Optional[OrderRead]:
        """Update order status."""
        db_order = self.order_repo.update_status(order_id, status)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
    def accept_order(self, order_id: int) -> OrderRead:
        """Accept an order (Order Staff) and log to outbox."""
        db_order = self.order_repo.update_status(order_id, OrderStatus.ACCEPTED)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.is_pending_recovery = True  # Mark for recovery
        
        # Log to outbox
        from app.models.outbox.outbox import Outbox
        outbox_event = Outbox(
            event_type="order_accepted",
            payload={"order_id": db_order.id}
        )
        self.db.add(outbox_event)
        self.db.commit()  # Ensure immediate persistence
        
        process_order_workflow.delay(db_order.id, "accepted")
        return OrderRead.model_validate(db_order)
        self.line_item_repo = OrderLineItemRepository(db)
        self.db = db
    def ship_order(self, order_id: int) -> OrderRead:
        """Ship an order (Order Staff) and log to outbox."""
        db_order = self.order_repo.update_status(order_id, OrderStatus.SHIPPED)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        db_order.is_pending_recovery = True  # Mark for recovery
        
        # Log to outbox
        from app.models.outbox.outbox import Outbox
        outbox_event = Outbox(
            event_type="order_shipped",
            payload={"order_id": db_order.id}
        )
        self.db.add(outbox_event)
        self.db.commit()  # Ensure immediate persistence
        
        process_order_workflow.delay(db_order.id, "shipped")
        return OrderRead.model_validate(db_order)
            raise HTTPException(status_code=404, detail="Order not found")
        process_order_workflow.delay(db_order.id, "shipped")
        return OrderRead.model_validate(db_order)

    def close_order(self, order_id: int) -> OrderRead:
        """Close an order (Order Staff)."""
        db_order = self.order_repo.update_status(order_id, OrderStatus.CLOSED)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        process_order_workflow.delay(db_order.id, "closed")
        return OrderRead.model_validate(db_order)

    def get_order(self, order_id: int) -> Optional[OrderRead]:
        """Get order by ID."""
        db_order = self.order_repo.get_by_id(order_id)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderRead.model_validate(db_order)

    def update_order_status(self, order_id: int, status: OrderStatus) -> Optional[OrderRead]:
        """Update order status."""
        db_order = self.order_repo.update_status(order_id, status)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        return OrderRead.model_validate(db_order)

    def list_orders(self) -> list[OrderRead]:
        """List all orders."""
        db_orders = self.order_repo.list_all()
        return [OrderRead.model_validate(order) for order in db_orders]