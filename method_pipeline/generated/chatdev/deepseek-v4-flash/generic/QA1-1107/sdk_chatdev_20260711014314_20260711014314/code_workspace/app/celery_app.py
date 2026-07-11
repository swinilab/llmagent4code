"""
Celery application configuration for production task queue.
Used for heavy background processing (notifications, report generation, etc.).
For local development, the in-process BackgroundTaskProcessor is used instead.
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "oms",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.celery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(bind=True, name="process_payment_notification")
def process_payment_notification(self, payment_id: str, order_id: str) -> dict:
    """Celery task: send payment notification (placeholder for external integration)."""
    return {"payment_id": payment_id, "order_id": order_id, "status": "notification_sent"}
