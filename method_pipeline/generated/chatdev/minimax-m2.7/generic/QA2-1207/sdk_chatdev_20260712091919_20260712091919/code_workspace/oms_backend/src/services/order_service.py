"""
Order Service - business logic for order management with full lifecycle support.
Handles: place order -> accept -> ship -> close workflow.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from ..domain.models import Order, OrderStatus, LineItem, Address, OrderSnapshot
from ..infrastructure.repositories import OrderRepository, StateSnapshotRepository
from ..utils.resilience import StateManager, FeatureFlags, CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)


class OrderWorkflowError(Exception):
    """Raised when order workflow transition is invalid."""
    pass


class OrderService:
    """
    Service layer for order operations with workflow management.
    Implements NFR 2.3 State Preservation through state snapshots and idempotency.
    """

    def __init__(self, db_session=None, state_manager: Optional[StateManager] = None,
                 feature_flags: Optional[FeatureFlags] = None):
        self.db_session = db_session
        self._repo = None
        self._snapshot_repo = None
        self._state_manager = state_manager or StateManager()
        self._feature_flags = feature_flags or FeatureFlags()
        self._circuit_breaker = CircuitBreaker("order_service", CircuitBreakerConfig())

    @property
    def repo(self) -> OrderRepository:
        if self._repo is None:
            if self.db_session:
                self._repo = OrderRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._repo

    @property
    def snapshot_repo(self) -> StateSnapshotRepository:
        if self._snapshot_repo is None:
            if self.db_session:
                self._snapshot_repo = StateSnapshotRepository(self.db_session)
            else:
                raise RuntimeError("No database session available")
        return self._snapshot_repo

    def _save_state_snapshot(self, order: Order, event: str):
        if self._feature_flags.is_enabled("audit_log_enabled"):
            snapshot = OrderSnapshot(
                timestamp=datetime.now(timezone.utc),
                order_id=order.id,
                status=order.status.value if hasattr(order.status, 'value') else order.status,
                pending_operations=[],
                last_processed_event=event
            )
            try:
                self.snapshot_repo.save_snapshot(snapshot)
                self._state_manager.save_snapshot(
                    "order", order.id, order.to_dict(), event
                )
            except Exception as e:
                logger.warning(f"Could not save state snapshot: {e}")

    def place_order(self, customer_id: str, line_items: List[LineItem],
                   shipping_address: Address, idempotency_key: Optional[str] = None,
                   notes: str = "") -> Order:
        """
        Step 1: Customer places order.
        Creates a new order in PENDING status.
        """
        for item in line_items:
            if item.quantity <= 0:
                raise ValueError(f"Invalid quantity for line item: {item.quantity}")

        order = Order(
            customer_id=customer_id,
            line_items=line_items,
            shipping_address=shipping_address,
            status=OrderStatus.PENDING,
            notes=notes,
            idempotency_key=idempotency_key
        )
        order.recalculate_totals()

        if idempotency_key:
            saved_order, created = self.repo.create_with_idempotency(order)
            if not created:
                logger.info(f"Returning existing order for idempotency key: {idempotency_key}")
                return saved_order
        else:
            saved_order = self.repo.create(order)

        self._save_state_snapshot(saved_order, "order_placed")
        logger.info(f"Order placed: {saved_order.id} for customer: {customer_id}")
        return saved_order

    def accept_order(self, order_id: str) -> Order:
        """
        Step 2: Order Staff accepts order.
        Transitions order from PENDING to ACCEPTED.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        if order.status != OrderStatus.PENDING:
            raise OrderWorkflowError(
                f"Cannot accept order in status {order.status}. Expected: {OrderStatus.PENDING}"
            )

        order.status = OrderStatus.ACCEPTED
        order.accepted_at = datetime.now(timezone.utc)
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_accepted")
        logger.info(f"Order accepted: {order_id}")
        return updated_order

    def reject_order(self, order_id: str, reason: str = "") -> Order:
        """
        Order Staff rejects order.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        if order.status != OrderStatus.PENDING:
            raise OrderWorkflowError(
                f"Cannot reject order in status {order.status}. Expected: {OrderStatus.PENDING}"
            )

        order.status = OrderStatus.REJECTED
        order.notes = f"{order.notes}\nRejection reason: {reason}".strip()
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_rejected")
        logger.info(f"Order rejected: {order_id}, reason: {reason}")
        return updated_order

    def mark_invoiced(self, order_id: str, invoice_id: str) -> Order:
        """
        Step 3 (triggered by accountant): Order becomes invoiced.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        if order.status != OrderStatus.ACCEPTED:
            raise OrderWorkflowError(
                f"Cannot mark as invoiced order in status {order.status}. Expected: {OrderStatus.ACCEPTED}"
            )

        order.status = OrderStatus.INVOICED
        order.invoice_id = invoice_id
        updated_order = self.repo.update(order)
        self._save_state_snapshot(updated_order, "order_invoiced")
        logger.info(f"Order marked as invoiced: {order_id}, invoice: {invoice_id}")
        return updated_order

    def mark_paid(self, order_id: str) -> Order:
        """
        Step 5 (after payment verified): Order becomes paid.
        Idempotent - can be called multiple times.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        current_status = order.status.value if hasattr(order.status, 'value') else order.status
        if current_status == "paid":
            logger.info(f"Order {order_id} is already paid, returning")
            return order

        if current_status not in ["invoiced", "paid"]:
            raise OrderWorkflowError(
                f"Cannot mark as paid order in status {order.status}. Expected: {OrderStatus.INVOICED}"
            )

        order.status = OrderStatus.PAID
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_paid")
        logger.info(f"Order marked as paid: {order_id}")
        return updated_order

    def ship_order(self, order_id: str, tracking_number: str = "") -> Order:
        """
        Step 6: Order Staff ships paid order.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        if order.status != OrderStatus.PAID:
            raise OrderWorkflowError(
                f"Cannot ship order in status {order.status}. Expected: {OrderStatus.PAID}"
            )

        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.now(timezone.utc)
        if tracking_number:
            order.notes = f"{order.notes}\nTracking: {tracking_number}".strip()
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_shipped")
        logger.info(f"Order shipped: {order_id}, tracking: {tracking_number}")
        return updated_order

    def close_order(self, order_id: str) -> Order:
        """
        Step 7: Order Staff closes completed order.
        """
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        if order.status != OrderStatus.SHIPPED:
            raise OrderWorkflowError(
                f"Cannot close order in status {order.status}. Expected: {OrderStatus.SHIPPED}"
            )

        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(timezone.utc)
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_completed")
        self._state_manager.clear_snapshot("order", order_id)
        logger.info(f"Order closed: {order_id}")
        return updated_order

    def cancel_order(self, order_id: str, reason: str = "") -> Order:
        """Cancel an order (only if not yet shipped)."""
        order = self.repo.get_by_id(order_id)
        if not order:
            raise OrderWorkflowError(f"Order not found: {order_id}")

        non_cancellable = [OrderStatus.SHIPPED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]
        if order.status in non_cancellable:
            raise OrderWorkflowError(
                f"Cannot cancel order in status {order.status}"
            )

        order.status = OrderStatus.CANCELLED
        order.notes = f"{order.notes}\nCancellation reason: {reason}".strip()
        updated_order = self.repo.update(order)

        self._save_state_snapshot(updated_order, "order_cancelled")
        logger.info(f"Order cancelled: {order_id}, reason: {reason}")
        return updated_order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.repo.get_by_id(order_id)

    def get_orders_by_customer(self, customer_id: str, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get orders for a customer."""
        return self.repo.get_by_customer(customer_id, skip=skip, limit=limit)

    def get_pending_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get orders pending review (for order staff)."""
        return self.repo.get_pending_orders(skip=skip, limit=limit)

    def get_orders_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get orders by status."""
        return self.repo.get_by_status(status, skip=skip, limit=limit)

    def recover_pending_orders(self) -> List[Order]:
        """
        NFR 2.3: Recover orders that may have been interrupted.
        Called on application startup.
        """
        pending_statuses = [
            OrderStatus.PENDING.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.INVOICED.value,
            OrderStatus.PAID.value
        ]
        
        recovered_orders = []
        for status in pending_statuses:
            orders = self.repo.get_by_status(status)
            for order in orders:
                snapshot = self._state_manager.get_snapshot("order", order.id)
                if snapshot:
                    logger.info(f"Found recovery snapshot for order: {order.id}")
                    recovered_orders.append(order)
        
        logger.info(f"Recovered {len(recovered_orders)} pending orders from snapshots")
        return recovered_orders


def get_order_service(db_session=None) -> OrderService:
    """Factory function to get order service."""
    return OrderService(db_session)
