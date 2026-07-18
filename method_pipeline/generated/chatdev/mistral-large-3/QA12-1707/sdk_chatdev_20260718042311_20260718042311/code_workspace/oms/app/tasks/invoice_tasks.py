"""
Invoice tasks for Celery.
"""
from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.invoice import Invoice, InvoiceStatus
import structlog

logger = structlog.get_logger(__name__)


@celery_app.task(name="process_invoice_task")
def process_invoice_task(invoice_id: int):
    """Process an invoice (e.g., send to customer)."""
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).get(invoice_id)
        if invoice:
            invoice.status = InvoiceStatus.SENT
            invoice.is_pending_recovery = False
            db.commit()
            logger.info("Processed invoice", invoice_id=invoice_id)
    except Exception as e:
        logger.error("Failed to process invoice", invoice_id=invoice_id, error=str(e))
        db.rollback()
    finally:
        db.close()