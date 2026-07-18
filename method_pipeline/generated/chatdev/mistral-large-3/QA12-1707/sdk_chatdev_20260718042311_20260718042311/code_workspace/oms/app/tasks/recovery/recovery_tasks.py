"""
Celery tasks for recovery operations.

These tasks ensure that the system can recover from crashes or failures by:
- Recovering pending orders, payments, and invoices.
- Reprocessing failed outbox events.
- Validating recovery logs to ensure consistency.
"""
from app.tasks.celery_app import celery_app
from app.services.recovery import RecoveryService
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(name="recover_pending_operations")
def recover_pending_operations():
    """Celery task to recover pending operations (orders, payments, invoices, outbox events)."""
    recovery_service = RecoveryService()
        # Recover in-progress orders (e.g., PAYMENT_PENDING, INVOICE_GENERATED)
        await recovery_service.recover_in_progress_orders()
        logger.info("Starting recovery of pending operations")
        # Recover pending orders, payments, and invoices
        await recovery_service.recover_pending_orders()
        await recovery_service.recover_pending_payments()
        await recovery_service.recover_pending_invoices()
        
        # Reprocess failed outbox events
        await recovery_service.recover_outbox_events()
        # Recover in-progress orders (e.g., PAYMENT_PENDING, INVOICE_GENERATED)
        recovery_service.recover_in_progress_orders()
        
        # Recover pending orders, payments, and invoices
        recovery_service.recover_pending_orders()
        recovery_service.recover_pending_payments()
        recovery_service.recover_pending_invoices()
        
        # Reprocess failed outbox events
        recovery_service.recover_outbox_events()
        
        # Clean up stale recovery logs
        recovery_service.cleanup_stale_logs(days=7)
        
        logger.info("Recovery completed successfully")
    except Exception as e:
        logger.error("Recovery failed", error=str(e))
        raise


@celery_app.task(bind=True, max_retries=3)
def retry_payment(self, order_id: int):
    """Idempotent payment retry task with exponential backoff."""
    recovery_service = RecoveryService()
    try:
        logger.info("Retrying payment for order", order_id=order_id)
        recovery_service._retry_payment(order_id)
    except Exception as e:
        logger.error("Payment retry failed", order_id=order_id, error=str(e))
        raise self.retry(exc=e, countdown=60)  # Exponential backoff