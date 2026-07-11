"""
Infrastructure layer: circuit breaker, health checks, state preservation (event log + recovery).
"""
from __future__ import annotations

import json
import threading
import time
from decimal import Decimal
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.domain import Order, OrderStatus, LineItem, utcnow
from app.models import (
    EventLogModel,
    OrderModel,
    engine,
)


# ======================================================================
# Circuit Breaker
# ======================================================================
class CircuitBreakerState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerError(RuntimeError):
    """Raised when the circuit breaker is open (infrastructure failure detected)."""
    pass


class CircuitBreaker:
    """Protects a downstream resource from cascading failures.

    Implements the standard closed -> open -> half-open -> closed cycle.
    Only infrastructure-level exceptions (ConnectionError, TimeoutError, OSError)
    count toward the failure threshold. Business-logic exceptions (ValueError, etc.)
    pass through without affecting the breaker state.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_requests: int = 3,
    ):
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_requests = half_open_max_requests

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_requests = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def call(self, func: Callable, fallback: Optional[Callable] = None, *args, **kwargs) -> Any:
        """Execute *func* if the circuit is closed/half-open, else call *fallback* or raise.

        Only infrastructure-level exceptions (ConnectionError, TimeoutError, OSError)
        count toward the failure threshold. Business-logic exceptions (ValueError, etc.)
        pass through without affecting the breaker state.
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if time.time() - (self._last_failure_time or 0) >= self._recovery_timeout:
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._half_open_requests = 0
                else:
                    if fallback:
                        return fallback()
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._half_open_requests >= self._half_open_max_requests:
                    if fallback:
                        return fallback()
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN (half-open limit reached)")
                self._half_open_requests += 1

        try:
            result = func(*args, **kwargs)
        except CircuitBreakerError:
            raise  # re-raise without counting
        except (ConnectionError, TimeoutError, OSError) as exc:
            # Only infrastructure-level failures count toward the breaker
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()
                if self._failure_count >= self._failure_threshold:
                    self._state = CircuitBreakerState.OPEN
            if fallback:
                return fallback()
            raise
        except Exception as exc:
            # Business-logic exceptions (ValueError, TypeError, etc.) pass through
            # without affecting the circuit breaker state.
            # Decrement _half_open_requests so business errors do not consume probe slots.
            with self._lock:
                if self._state == CircuitBreakerState.HALF_OPEN:
                    self._half_open_requests = max(0, self._half_open_requests - 1)
            raise exc

        with self._lock:
            self._failure_count = 0
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.CLOSED
                self._half_open_requests = 0
        return result

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._half_open_requests = 0


# Singleton circuit breakers for non-essential subsystems
invoice_circuit = CircuitBreaker(
    "invoice",
    failure_threshold=settings.circuit_breaker_failure_threshold,
    recovery_timeout=settings.circuit_breaker_recovery_timeout,
    half_open_max_requests=settings.circuit_breaker_half_open_max_requests,
)

shipping_circuit = CircuitBreaker(
    "shipping",
    failure_threshold=settings.circuit_breaker_failure_threshold,
    recovery_timeout=settings.circuit_breaker_recovery_timeout,
    half_open_max_requests=settings.circuit_breaker_half_open_max_requests,
)

# Core checkout circuit - higher threshold, never degrades core
checkout_circuit = CircuitBreaker(
    "checkout",
    failure_threshold=settings.circuit_breaker_failure_threshold * 2,
    recovery_timeout=settings.circuit_breaker_recovery_timeout,
    half_open_max_requests=settings.circuit_breaker_half_open_max_requests,
)

# Payment circuit - non-core, can degrade under contention
payment_circuit = CircuitBreaker(
    "payment",
    failure_threshold=settings.circuit_breaker_failure_threshold,
    recovery_timeout=settings.circuit_breaker_recovery_timeout,
    half_open_max_requests=settings.circuit_breaker_half_open_max_requests,
)


def get_circuit_breaker_states() -> dict[str, str]:
    return {
        "invoice": invoice_circuit.state,
        "shipping": shipping_circuit.state,
        "checkout": checkout_circuit.state,
        "payment": payment_circuit.state,
    }


# ======================================================================
# Health Check
# ======================================================================
def check_database_health() -> str:
    """Return 'healthy' or an error message."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "healthy"
    except Exception as exc:
        return f"unhealthy: {exc}"


# ======================================================================
# State Preservation - Event Log
# ======================================================================
def append_event(
    session: Session,
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Persist a domain event to the event log."""
    log = EventLogModel(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=json.dumps(payload, default=str),
    )
    session.add(log)


def recover_pending_orders(session: Session) -> list[dict[str, Any]]:
    """On startup, scan for orders in a non-terminal state and log recovery.

    Returns a list of recovered order summaries.
    """
    terminal_statuses = {OrderStatus.CLOSED, OrderStatus.CANCELLED}
    pending_orders = (
        session.query(OrderModel)
        .filter(OrderModel.status.notin_(terminal_statuses))  # type: ignore[attr-defined]
        .all()
    )

    recovered = []
    for order in pending_orders:
        append_event(
            session,
            "Order",
            order.id,
            "OrderRecovered",
            {
                "order_id": order.id,
                "status": order.status.value,
                "customer_id": order.customer_id,
                "recovered_at": utcnow().isoformat(),
            },
        )
        recovered.append(
            {
                "order_id": order.id,
                "status": order.status.value,
                "customer_id": order.customer_id,
            }
        )
    session.commit()
    return recovered


def rebuild_order_from_events(aggregate_id: str) -> Optional[Order]:
    """Replay event log for a single order to rebuild its state (future use)."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        events = (
            session.query(EventLogModel)
            .filter(
                EventLogModel.aggregate_type == "Order",
                EventLogModel.aggregate_id == aggregate_id,
            )
            .order_by(EventLogModel.id)
            .all()
        )
        if not events:
            return None

        order = Order(id=UUID(aggregate_id))
        for evt in events:
            payload = json.loads(evt.payload)
            if evt.event_type == "OrderPlaced":
                order.customer_id = UUID(payload["customer_id"])
                order.status = OrderStatus.PENDING
                for item in payload.get("line_items", []):
                    order.line_items.append(
                        LineItem(
                            id=UUID(item.get("id", "00000000-0000-0000-0000-000000000000")),
                            product_id=UUID(item["product_id"]),
                            quantity=item["quantity"],
                            unit_price=Decimal(str(item["unit_price"])),
                            currency=item.get("currency", "USD"),
                        )
                    )
            elif evt.event_type == "OrderAccepted":
                order.status = OrderStatus.ACCEPTED
            elif evt.event_type == "OrderInvoiced":
                order.status = OrderStatus.INVOICED
                order.invoice_id = UUID(payload["invoice_id"])
            elif evt.event_type == "OrderPaid":
                order.status = OrderStatus.PAID
                order.payment_id = UUID(payload["payment_id"])
            elif evt.event_type == "OrderShipped":
                order.status = OrderStatus.SHIPPED
            elif evt.event_type == "OrderClosed":
                order.status = OrderStatus.CLOSED
            elif evt.event_type == "OrderCancelled":
                order.status = OrderStatus.CANCELLED
        return order
    finally:
        session.close()
