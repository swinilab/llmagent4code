"""
Celery tasks for order processing.
"""
from app.tasks.celery_app import celery_app
from app.models.order import OrderStatus
from app.db.session import SessionLocal
from app.services.order import OrderService


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority",  # High priority for core workflows
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high_priority"  # High priority for core workflows
)
def update_order_status_task(self, order_id: str, status: str):
    """Update order status asynchronously with idempotency and recovery."""
    from app.db.session import async_session
    from app.services.order import OrderService
    import structlog

    logger = structlog.get_logger(__name__)
    async_session_local = async_session
    
    async with async_session_local() as session:
        try:
            service = OrderService(session)
            order = await service.order_repo.get_by_id(order_id)
            if order and order.status != status:
                await service.update_order_status(order_id, status)
                order.is_pending_recovery = False
                await session.commit()
                logger.info("Updated order status", order_id=order_id, status=status)
            else:
                logger.info("Skipping task, order already processed", order_id=order_id, status=status)
        except Exception as e:
            await session.rollback()
            logger.error("Task failed", order_id=order_id, error=str(e))
            raise self.retry(exc=e)