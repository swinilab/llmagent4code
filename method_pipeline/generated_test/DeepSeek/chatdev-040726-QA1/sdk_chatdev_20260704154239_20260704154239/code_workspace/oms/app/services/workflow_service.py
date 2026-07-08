"""
Workflow orchestrator — enforces the order lifecycle state machine
with full transactional atomicity across multi-step operations.
"""
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.order import OrderStatusUpdate
from app.schemas.invoice import InvoiceCreate, InvoiceStatusUpdate
from app.schemas.payment import PaymentCreate
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.invoice_service import InvoiceService


class WorkflowError(Exception):
    """Raised when a workflow transition is invalid."""


class WorkflowService:
    """
    Orchestrates the 7-step order lifecycle.

    Steps:
      1. Customer places order  → PENDING
      2. Staff accepts          → ACCEPTED
      3. Accountant creates inv → INVOICED
      4. Customer pays          → PAID
      5. Accountant verifies    → VERIFIED
      6. Staff ships            → SHIPPED
      7. Staff closes           → CLOSED

    All methods use commit=False + explicit db.commit() to guarantee
    atomicity — if any step fails, all changes are rolled back.
    This ensures consistency across single-step and multi-step transitions.

    Note: skip_validation=True is passed to OrderService.update_status()
    because this class already validates transitions via _validate_transition().
    This avoids redundant validation and prevents the two state maps from
    diverging.
    """

    VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
        OrderStatus.PENDING: {OrderStatus.ACCEPTED},
        OrderStatus.ACCEPTED: {OrderStatus.INVOICED},
        OrderStatus.INVOICED: {OrderStatus.PAID},
        OrderStatus.PAID: {OrderStatus.VERIFIED},
        OrderStatus.VERIFIED: {OrderStatus.SHIPPED},
        OrderStatus.SHIPPED: {OrderStatus.CLOSED},
        OrderStatus.CLOSED: set(),
    }

    @staticmethod
    def _validate_transition(order: Order, target: OrderStatus) -> None:
        allowed = WorkflowService.VALID_TRANSITIONS.get(order.status, set())
        if target not in allowed:
            raise WorkflowError(
                f"Cannot transition from {order.status.value} to {target.value}. "
                f"Allowed targets: {[s.value for s in allowed] or 'none'}"
            )

    # --- Step 1: Customer places order (handled by OrderService.create) ---

    # --- Step 2: Order Staff reviews & accepts ---
    @staticmethod
    def accept_order(db: Session, order_id: str) -> Order:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            raise WorkflowError(f"Order {order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.ACCEPTED)
        order = OrderService.update_status(
            db, order_id, OrderStatusUpdate(status=OrderStatus.ACCEPTED),
            commit=False, skip_validation=True
        )
        db.commit()
        db.refresh(order)
        return order

    # --- Step 3: Accountant creates invoice (atomic multi-step) ---
    @staticmethod
    def create_invoice_for_order(db: Session, order_id: str, billing_info: str) -> Invoice:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            raise WorkflowError(f"Order {order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.INVOICED)

        # All operations in a single transaction
        invoice = InvoiceService.create(
            db,
            InvoiceCreate(
                order_id=order_id,
                billing_info=billing_info,
                amount=order.total_amount,
                currency=order.currency,
            ),
            commit=False,
        )
        invoice = InvoiceService.issue(db, invoice.id, commit=False)
        OrderService.update_status(
            db, order_id, OrderStatusUpdate(status=OrderStatus.INVOICED), commit=False, skip_validation=True
        )
        # SQLAlchemy identity map ensures order is still tracked; no need for get_by_id
        order.invoice_ref = invoice.id

        db.commit()
        db.refresh(invoice)
        return invoice

    # --- Step 4: Customer pays invoice (atomic multi-step) ---
    @staticmethod
    def pay_invoice(db: Session, invoice_id: str, payment_method: PaymentMethod) -> Payment:
        invoice = InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            raise WorkflowError(f"Invoice {invoice_id} not found")
        order = OrderService.get_by_id(db, invoice.order_id)
        if not order:
            raise WorkflowError(f"Order {invoice.order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.PAID)

        # All operations in a single transaction
        payment = PaymentService.create(
            db,
            PaymentCreate(
                order_id=order.id,
                amount=invoice.amount,
                currency=invoice.currency,
                method=payment_method,
            ),
            commit=False,
        )
        payment = PaymentService.mark_paid(db, payment.id, commit=False)
        InvoiceService.update_status(db, invoice_id, InvoiceStatusUpdate(status=InvoiceStatus.PAID), commit=False)
        OrderService.update_status(
            db, order.id, OrderStatusUpdate(status=OrderStatus.PAID), commit=False, skip_validation=True
        )

        db.commit()
        db.refresh(payment)
        return payment

    # --- Step 5: Accountant verifies payment (atomic multi-step) ---
    @staticmethod
    def verify_payment(db: Session, payment_id: str) -> Payment:
        payment = PaymentService.get_by_id(db, payment_id)
        if not payment:
            raise WorkflowError(f"Payment {payment_id} not found")
        order = OrderService.get_by_id(db, payment.order_id)
        if not order:
            raise WorkflowError(f"Order {payment.order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.VERIFIED)

        # All operations in a single transaction
        payment = PaymentService.verify(db, payment_id, commit=False)
        OrderService.update_status(
            db, order.id, OrderStatusUpdate(status=OrderStatus.VERIFIED), commit=False, skip_validation=True
        )

        db.commit()
        db.refresh(payment)
        return payment

    # --- Step 6: Order Staff ships paid order ---
    @staticmethod
    def ship_order(db: Session, order_id: str) -> Order:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            raise WorkflowError(f"Order {order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.SHIPPED)
        order = OrderService.update_status(
            db, order_id, OrderStatusUpdate(status=OrderStatus.SHIPPED),
            commit=False, skip_validation=True
        )
        db.commit()
        db.refresh(order)
        return order

    # --- Step 7: Order Staff closes completed order ---
    @staticmethod
    def close_order(db: Session, order_id: str) -> Order:
        order = OrderService.get_by_id(db, order_id)
        if not order:
            raise WorkflowError(f"Order {order_id} not found")
        WorkflowService._validate_transition(order, OrderStatus.CLOSED)
        order = OrderService.update_status(
            db, order_id, OrderStatusUpdate(status=OrderStatus.CLOSED),
            commit=False, skip_validation=True
        )
        db.commit()
        db.refresh(order)
        return order
