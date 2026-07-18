"""
Payment tasks for Celery.
"""
from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.payment import Payment, PaymentStatus
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(name="process_payment_task")
def process_payment_task(payment_id: int):
    """Process a payment (e.g., verify with bank)."""
    db = SessionLocal()
    try:
        payment = db.query(Payment).get(payment_id)
        if payment:
            payment.status = PaymentStatus.COMPLETED
            payment.is_pending_recovery = False
            db.commit()
            logger.info("Processed payment", payment_id=payment_id)
    except Exception as e:
        logger.error("Failed to process payment", payment_id=payment_id, error=str(e))
        db.rollback()
    finally:
        db.close()