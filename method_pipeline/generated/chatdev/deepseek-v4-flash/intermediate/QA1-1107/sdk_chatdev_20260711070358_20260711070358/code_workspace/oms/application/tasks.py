"""
Background tasks for deferrable work.
These are executed by RQ workers, decoupled from request threads.
"""
import logging
from oms.infrastructure.logging import get_logger

logger = get_logger(__name__)


def generate_invoice_task(order_id: str, customer_id: str) -> None:
    """
    Generate an invoice PDF or document.
    This is a deferrable task - not on the critical path.
    """
    logger.info(
        "Generating invoice document",
        extra={"order_id": order_id, "customer_id": customer_id},
    )
    # In production, this would generate a PDF, store it, etc.
    # For this implementation, we log the action.
    logger.info(
        "Invoice document generated",
        extra={"order_id": order_id, "customer_id": customer_id},
    )


def send_notification_task(customer_id: str, message: str) -> None:
    """
    Send a notification to a customer (email, SMS, etc.).
    This is a deferrable task - not on the critical path.
    """
    logger.info(
        "Sending notification",
        extra={"customer_id": customer_id, "message": message},
    )
    # In production, this would send an email/SMS/push notification.
    logger.info(
        "Notification sent",
        extra={"customer_id": customer_id, "message": message},
    )
