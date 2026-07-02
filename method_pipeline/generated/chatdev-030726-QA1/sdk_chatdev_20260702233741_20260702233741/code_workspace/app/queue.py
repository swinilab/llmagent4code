# app/queue.py
"""
Celery task definitions for the OMS backend.

The module provides two asynchronous tasks:
* `verify_payment_task` – updates a Payment record and, on success,
  marks the related Order as PAID.
* `ship_order_task` – marks a PAID Order as SHIPPED.

If Celery is not installed (e.g., during simple local testing), a
light‑weight stub is used that executes the task synchronously when
`.delay()` is called.
"""

from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------------
# Optional Celery import – provide a minimal stub when Celery is absent.
# ---------------------------------------------------------------------------
try:
    from celery import Celery  # type: ignore
except ImportError:  # pragma: no cover
    class _SyncTask:
        """Simple wrapper that mimics Celery's .delay() API."""

        def __init__(self, func):
            self._func = func

        def delay(self, *args: Any, **kwargs: Any) -> Any:
            """Execute the wrapped function synchronously."""
            return self._func(*args, **kwargs)

        __call__ = delay  # allow direct call as well

    class Celery:  # type: ignore
        """Very small stub that mimics the parts of Celery we need."""

        def __init__(self, *_, **__):
            self.conf = type("conf", (), {"task_routes": {}})()

        def task(self, *_, **__) -> Any:  # noqa: D401
            """Decorator that returns a sync‑task wrapper."""
            def decorator(func):
                return _SyncTask(func)
            return decorator

# ---------------------------------------------------------------------------
# Celery application configuration
# ---------------------------------------------------------------------------
from app.config import settings

celery_app = Celery(
    "oms",
    broker=getattr(settings, "CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=getattr(settings, "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Explicit routing – keeps payment‑related work separate from shipping.
celery_app.conf.task_routes = {
    "app.queue.verify_payment_task": {"queue": "payments"},
    "app.queue.ship_order_task": {"queue": "shipping"},
}

# ---------------------------------------------------------------------------
# Task: verify_payment_task
# ---------------------------------------------------------------------------
@celery_app.task(name="app.queue.verify_payment_task")
def verify_payment_task(payment_id: int, success: bool) -> Dict[str, Any]:
    """
    Verify a payment and update the related order.

    Args:
        payment_id: Primary key of the Payment to verify.
        success:   ``True`` if the payment succeeded, ``False`` otherwise.

    Returns:
        A dictionary with the outcome, e.g.:
        {
            "payment_id": 12,
            "status": "completed",
            "order_id": 5,
            "order_status": "paid"
        }
        If the payment does not exist, ``{"error": "payment not found"}`` is returned.
    """
    from app.dependencies import SessionLocal
    from app.models import Payment, Order, PaymentStatus, OrderStatus

    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return {"error": "payment not found"}

        # Update payment status
        payment.status = PaymentStatus.COMPLETED if success else PaymentStatus.FAILED
        db.add(payment)

        result = {"payment_id": payment.id, "status": payment.status.value}

        # On successful verification, mark the order as PAID
        if success:
            order = db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.status = OrderStatus.PAID
                db.add(order)
                result.update({"order_id": order.id, "order_status": order.status.value})
        db.commit()
        return result
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Task: ship_order_task
# ---------------------------------------------------------------------------
@celery_app.task(name="app.queue.ship_order_task")
def ship_order_task(order_id: int) -> Dict[str, Any]:
    """
    Mark an order as shipped.

    The task is enqueued after a successful payment.  It changes the order
    status from PAID to SHIPPED.

    Args:
        order_id: Primary key of the Order to ship.

    Returns:
        ``{"order_id": <id>, "status": "shipped"}`` on success,
        or ``{"error": "order not found"}`` if the order does not exist.
    """
    from app.dependencies import SessionLocal
    from app.models import Order, OrderStatus

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"error": "order not found"}

        # Only ship orders that are already PAID
        if order.status != OrderStatus.PAID:
            return {"order_id": order.id, "error": f"cannot ship order in state {order.status.value}"}

        order.status = OrderStatus.SHIPPED
        db.add(order)
        db.commit()
        return {"order_id": order.id, "status": order.status.value}
    finally:
        db.close()
