"""
Celery task definitions for production background processing.
"""
from app.celery_app import celery_app


@celery_app.task(bind=True, name="send_order_confirmation")
def send_order_confirmation(self, order_id: str, customer_email: str) -> dict:
    """Send order confirmation email (placeholder for email service integration)."""
    return {"order_id": order_id, "customer_email": customer_email, "status": "sent"}


@celery_app.task(bind=True, name="generate_daily_report")
def generate_daily_report(self) -> dict:
    """Generate daily sales report (placeholder for reporting integration)."""
    return {"status": "report_generated"}
