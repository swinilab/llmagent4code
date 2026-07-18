"""
Celery application setup.
"""
from celery import Celery
from app.core.config import settings
celery_app = Celery(
    "oms_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
celery_app = Celery(
    "oms_tasks",
    broker="redis://redis:6379/0",  # Use Redis with persistence
    backend="redis://redis:6379/0",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,  # Ensure tasks are re-queued if worker crashes
    broker_connection_retry_on_startup=True,
    task_default_priority=5,  # Default priority for tasks
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "high_priority": {"exchange": "high_priority", "routing_key": "high_priority"},
    },
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour visibility timeout
        "max_retries": 3,  # Retry failed tasks 3 times
    },
)
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.order_tasks.update_order_status_task": {"queue": "high_priority"},
    },
)
)