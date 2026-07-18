"""
Recovery service for pending orders, invoices, payments, and outbox events.

This service ensures that the system can recover from crashes or failures by restoring
pending operations to their correct state. It handles:
- Orders stuck in intermediate states (e.g., PAYMENT_PENDING, INVOICE_GENERATED).
- Payments and invoices stuck in PENDING.
- Failed outbox events that were not processed.
- Validation of recovery logs to ensure consistency.
"""
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from app.db.session import async_session
from app.models.order import Order, OrderStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentStatus
from app.models.outbox.outbox import Outbox, RecoveryLog
from app.tasks.order_tasks import update_order_status_task
from app.tasks.invoice_tasks import generate_invoice_task
from app.models.outbox.outbox import Outbox
from app.models.recovery_log import RecoveryLog
import uuid
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class RecoveryService:
    """Recovery service for pending orders, invoices, payments, and outbox events."""
    def __init__(self, db: Session = None):
        self.db = db
        self.logger = structlog.get_logger(__name__)

                    await self._retry_payment(order.id, session)
        """Recover orders stuck in intermediate states (e.g., PAYMENT_PENDING, INVOICE_GENERATED)."""
        async with async_session() as session:
            try:
                # Recover orders stuck in PAYMENT_PENDING
                    if payment and payment.status == PaymentStatus.COMPLETED:
                    select(Order).where(Order.status == OrderStatus.PAYMENT_PENDING)
                )
                for order in pending_payments.scalars():
                    payment = await session.execute(
                        select(Payment).where(Payment.order_id == order.id)
                    ).scalar_one_or_none()
                    if payment and payment.status == PaymentStatus.COMPLETED:
                        order.status = OrderStatus.PAID
                        self.logger.info("Recovered order from PAYMENT_PENDING to PAID", order_id=order.id)
                        await self._retry_payment(order.id, session)
                        # Retry payment processing
                        await self._retry_payment(order.id)
                    await session.commit()

                    elif payment and payment.status == PaymentStatus.PENDING:
                invoice_orders = await session.execute(
                    select(Order).where(Order.status == OrderStatus.INVOICE_GENERATED)
                )
                for order in invoice_orders.scalars():
                        await self._regenerate_invoice(order.id, session)
                        select(Invoice).where(Invoice.order_id == order.id)
                    ).scalar_one_or_none()
                    if not invoice:
                        # Regenerate invoice
                    if invoice and invoice.status == InvoiceStatus.ISSUED:
                    await session.commit()

                self.logger.info("Completed recovery of in-progress orders")
            except Exception as e:
                self.logger.error("Failed to recover in-progress orders", error=str(e))
                await session.rollback()
                raise

    async def recover_pending_orders(self):
        """Recover orders stuck in PENDING_ACCEPTANCE with idempotency."""
        async with async_session() as session:
            try:
                pending_orders = await session.execute(
                    select(Order).where(
                        await self._log_recovery(session, order.id, "ORDER", "SUCCESS")
                        Order.is_pending_recovery == True
                    )
                )
                for order in pending_orders.scalars():
                    if order.status == OrderStatus.PENDING_ACCEPTANCE:
                        self.logger.info("Recovering pending order", order_id=order.id)
                        update_order_status_task.apply_async(
                            (order.id, OrderStatus.ACCEPTED.value),
                            countdown=10,
                            priority=5
                        )
                        await self._log_recovery(session, order.id, "ORDER", "SUCCESS")
                    else:
                        self.logger.warning(
                            "Order not in PENDING_ACCEPTANCE, skipping recovery", 
                            order_id=order.id, 
                            current_status=order.status
                        )
                await session.commit()
    async def _retry_payment(self, order_id: str, session):
        """Retry payment for an order."""
        try:
            payment = await session.execute(
                select(Payment).where(Payment.order_id == order_id)
            ).scalar_one_or_none()
            if payment and payment.status == PaymentStatus.PENDING:
                process_payment_task.apply_async(
                    (payment.id,),
                    countdown=10,
                    priority=5
                )
                self.logger.info("Retried payment for order", order_id=order_id)
        except Exception as e:
            self.logger.error("Failed to retry payment", order_id=order_id, error=str(e))
            raise

    async def _regenerate_invoice(self, order_id: str, session):
        """Regenerate invoice for an order."""
        try:
            order = await session.execute(
                select(Order).where(Order.id == order_id)
            ).scalar_one_or_none()
            if order and order.status == OrderStatus.INVOICE_GENERATED:
                generate_invoice_task.apply_async(
                    (order.id,),
                    countdown=10,
                    priority=5
                )
                self.logger.info("Regenerated invoice for order", order_id=order_id)
        except Exception as e:
            self.logger.error("Failed to regenerate invoice", order_id=order_id, error=str(e))
            raise

    async def _log_recovery(self, session, aggregate_id: str, aggregate_type: str, status: str):
        """Log recovery operation to recovery_log table."""
        try:
            recovery_log = RecoveryLog(
                id=str(uuid.uuid4()),
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                status=status,
                checkpoint_data={"recovered_at": datetime.utcnow().isoformat()}
            )
            session.add(recovery_log)
            await session.commit()
            self.logger.info("Logged recovery", aggregate_id=aggregate_id, status=status)
        except Exception as e:
            self.logger.error("Failed to log recovery", aggregate_id=aggregate_id, error=str(e))
            await session.rollback()
            raise

    async def recover_pending_payments(self):
        """Recover payments stuck in PENDING."""
        async with async_session() as session:
            try:
                pending_payments = await session.execute(
                    select(Payment).where(Payment.status == PaymentStatus.PENDING)
                )
                for payment in pending_payments.scalars():
                    process_payment_task.apply_async(
                        (payment.id,),
                        countdown=10,
                        priority=5
                    )
                    await self._log_recovery(session, payment.id, "PAYMENT", "SUCCESS")
                await session.commit()
                self.logger.info("Completed recovery of pending payments")
            except Exception as e:
                self.logger.error("Failed to recover pending payments", error=str(e))
                await session.rollback()
                raise

    async def recover_pending_invoices(self):
        """Recover invoices stuck in PENDING."""
        async with async_session() as session:
            try:
                pending_invoices = await session.execute(
                    select(Invoice).where(Invoice.status == InvoiceStatus.PENDING)
                )
                for invoice in pending_invoices.scalars():
                    generate_invoice_task.apply_async(
                        (invoice.order_id,),
                        countdown=10,
                        priority=5
                    )
                    await self._log_recovery(session, invoice.id, "INVOICE", "SUCCESS")
                await session.commit()
                self.logger.info("Completed recovery of pending invoices")
            except Exception as e:
                self.logger.error("Failed to recover pending invoices", error=str(e))
                await session.rollback()
                raise

    async def recover_outbox_events(self):
        """Reprocess failed outbox events."""
        async with async_session() as session:
            try:
                failed_events = await session.execute(
                    select(Outbox).where(Outbox.processed == False)
                )
                for event in failed_events.scalars():
                    if event.event_type == "ORDER_PLACED":
                        update_order_status_task.apply_async(
                            (event.payload["order_id"], OrderStatus.ACCEPTED.value),
                            countdown=10,
                            priority=5
                        )
                    elif event.event_type == "PAYMENT_COMPLETED":
                        update_order_status_task.apply_async(
                            (event.payload["order_id"], OrderStatus.PAID.value),
                            countdown=10,
                            priority=5
                        )
                    event.processed = True
                    await self._log_recovery(session, event.id, "OUTBOX", "SUCCESS")
                await session.commit()
                self.logger.info("Completed reprocessing of failed outbox events")
            except Exception as e:
                self.logger.error("Failed to reprocess outbox events", error=str(e))
                await session.rollback()
                raise

    async def cleanup_stale_logs(self, days: int = 7):
        """Clean up stale recovery logs older than `days`."""
        async with async_session() as session:
            try:
                cutoff = datetime.utcnow() - timedelta(days=days)
                stale_logs = await session.execute(
                    select(RecoveryLog).where(RecoveryLog.created_at < cutoff)
                )
                for log in stale_logs.scalars():
                    await session.delete(log)
                await session.commit()
                self.logger.info("Cleaned up stale recovery logs", days=days)
            except Exception as e:
                self.logger.error("Failed to clean up stale logs", error=str(e))
                await session.rollback()
                raise
                            countdown=10,
                            priority=5
                        )
                        await self._log_recovery(session, invoice.id, "INVOICE", "SUCCESS")
                    else:
                        self.logger.warning(
                            "Invoice not in PENDING, skipping recovery", 
                            invoice_id=invoice.id, 
                            current_status=invoice.status
                        )
                await session.commit()
            except Exception as e:
                self.logger.error("Failed to recover pending invoices", error=str(e))
                await session.rollback()
                raise

    async def recover_outbox_events(self):
        """Reprocess failed outbox events with exponential backoff."""
        async with async_session() as session:
            try:
                failed_events = await session.execute(
                    select(Outbox).where(Outbox.processed == False)
                )
                for event in failed_events.scalars():
                    recovery_log = await session.execute(
                        select(RecoveryLog).where(RecoveryLog.event_id == event.id)
                    ).scalar_one_or_none()

                    if recovery_log and recovery_log.status == "PROCESSED":
                        self.logger.info("Skipping already processed event", event_id=event.id)
                        continue

                    self.logger.info("Replaying outbox event", event_id=event.id, event_type=event.event_type)

                    if event.event_type == "ORDER_PLACED":
                        update_order_status_task.apply_async(
                            (event.payload["order_id"], OrderStatus.REVIEWED.value),
                            countdown=10,
                            priority=5,
                        )
                    elif event.event_type == "PAYMENT_PROCESSED":
                        update_order_status_task.apply_async(
                            (event.payload["order_id"], OrderStatus.PAID.value),
                            countdown=10,
                            priority=5,
                        )
                    elif event.event_type == "INVOICE_GENERATED":
                        update_order_status_task.apply_async(
                            (event.payload["order_id"], OrderStatus.INVOICED.value),
                            countdown=10,
                            priority=5,
                        )

                    # Log recovery progress
                    await self._log_recovery(session, event.id, "OUTBOX_EVENT", "PROCESSED")
                    event.processed = True
                    await session.commit()
            except Exception as e:
                self.logger.error("Outbox replay failed", error=str(e))
                await session.rollback()
                raise

    async def _retry_payment(self, order_id: int):
        """Retry payment processing for an order."""
        try:
            self.logger.info("Retrying payment for order", order_id=order_id)
            process_payment_task.apply_async(
                (order_id,),
                countdown=10,
                priority=5
            )
        except Exception as e:
            self.logger.error("Failed to retry payment", order_id=order_id, error=str(e))
            raise

    async def _regenerate_invoice(self, order_id: int):
        """Regenerate invoice for an order."""
        try:
            self.logger.info("Regenerating invoice for order", order_id=order_id)
            generate_invoice_task.apply_async(
                (order_id,),
                countdown=10,
                priority=5
            )
        except Exception as e:
            self.logger.error("Failed to regenerate invoice", order_id=order_id, error=str(e))
            raise

    async def _log_recovery(self, session, entity_id: str, entity_type: str, status: str):
        """Log recovery progress for an entity."""
        try:
            recovery_log = RecoveryLog(
                event_id=entity_id,
                entity_type=entity_type,
                status=status,
                created_at=datetime.utcnow()
            )
            session.add(recovery_log)
            await session.commit()
        except Exception as e:
            self.logger.error("Failed to log recovery", entity_id=entity_id, error=str(e))
            await session.rollback()
            raise

    async def validate_recovery(self, order_id: int):
        """Validate that the recovery log matches the actual state of the order."""
        async with async_session() as session:
            try:
                recovery_log = await session.execute(
                    select(RecoveryLog).where(RecoveryLog.event_id == order_id)
                ).scalar_one_or_none()

                if not recovery_log:
                    self.logger.warning("No recovery log found for order", order_id=order_id)
                    return False

                order = await session.execute(
                    select(Order).where(Order.id == order_id)
                ).scalar_one_or_none()

                if not order:
                    self.logger.warning("Order not found", order_id=order_id)
                    return False

                if order.status != recovery_log.expected_status:
                    self.logger.error(
                        "Recovery validation failed", 
                        order_id=order_id, 
                        expected_status=recovery_log.expected_status, 
                        actual_status=order.status
                    )
                    return False

                self.logger.info("Recovery validation passed", order_id=order_id)
                return True
            except Exception as e:
                self.logger.error("Recovery validation failed", order_id=order_id, error=str(e))
                raise

    async def cleanup_stale_logs(self, days: int = 7):
        """Clean up stale recovery logs older than `days`."""
        async with async_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                stale_logs = await session.execute(
                    select(RecoveryLog).where(RecoveryLog.created_at < cutoff_date)
                )
                for log in stale_logs.scalars():
                    await session.delete(log)
                await session.commit()
                self.logger.info("Cleaned up stale recovery logs", days=days)
            except Exception as e:
                self.logger.error("Failed to clean up stale logs", error=str(e))
                await session.rollback()
                raise