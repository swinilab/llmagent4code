"""
Service layer for Invoice operations.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceStatusUpdate


class InvoiceStateError(Exception):
    """Raised when an invalid invoice state transition is attempted."""


class InvoiceService:
    """Business logic for managing invoices."""

    @staticmethod
    def create(db: Session, data: InvoiceCreate, commit: bool = True) -> Invoice:
        invoice = Invoice(
            order_id=data.order_id,
            billing_info=data.billing_info,
            amount=data.amount,
            currency=data.currency,
            status=InvoiceStatus.DRAFT,
        )
        db.add(invoice)
        if commit:
            db.commit()
            db.refresh(invoice)
        else:
            db.flush()
        return invoice

    @staticmethod
    def get_by_id(db: Session, invoice_id: str) -> Invoice | None:
        return (
            db.query(Invoice)
            .options(joinedload(Invoice.order))
            .filter(Invoice.id == invoice_id)
            .first()
        )

    @staticmethod
    def list_by_order(db: Session, order_id: str) -> list[Invoice]:
        return (
            db.query(Invoice)
            .options(joinedload(Invoice.order))
            .filter(Invoice.order_id == order_id)
            .all()
        )

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Invoice]:
        return (
            db.query(Invoice)
            .options(joinedload(Invoice.order))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def issue(db: Session, invoice_id: str, commit: bool = True) -> Invoice | None:
        invoice = InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.DRAFT:
            raise InvoiceStateError(
                f"Cannot issue invoice {invoice_id}: current status is {invoice.status.value}, "
                f"expected 'draft'"
            )
        invoice.status = InvoiceStatus.ISSUED
        invoice.issue_date = datetime.now(timezone.utc)
        invoice.due_date = datetime.now(timezone.utc) + timedelta(days=30)
        if commit:
            db.commit()
            db.refresh(invoice)
        else:
            db.flush()
        return invoice

    @staticmethod
    def update_status(db: Session, invoice_id: str, data: InvoiceStatusUpdate, commit: bool = True) -> Invoice | None:
        invoice = InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return None
        # Only allow specific transitions
        allowed_from_draft = {InvoiceStatus.ISSUED, InvoiceStatus.CANCELLED}
        allowed_from_issued = {InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED}
        allowed_from_paid = {InvoiceStatus.CANCELLED}
        allowed_from_overdue = {InvoiceStatus.CANCELLED}

        if invoice.status == InvoiceStatus.DRAFT and data.status not in allowed_from_draft:
            raise InvoiceStateError(
                f"Cannot transition invoice {invoice_id} from 'draft' to '{data.status.value}'"
            )
        elif invoice.status == InvoiceStatus.ISSUED and data.status not in allowed_from_issued:
            raise InvoiceStateError(
                f"Cannot transition invoice {invoice_id} from 'issued' to '{data.status.value}'"
            )
        elif invoice.status == InvoiceStatus.PAID and data.status not in allowed_from_paid:
            raise InvoiceStateError(
                f"Cannot transition invoice {invoice_id} from 'paid' to '{data.status.value}'"
            )
        elif invoice.status == InvoiceStatus.OVERDUE and data.status not in allowed_from_overdue:
            raise InvoiceStateError(
                f"Cannot transition invoice {invoice_id} from 'overdue' to '{data.status.value}'"
            )
        elif invoice.status == InvoiceStatus.CANCELLED:
            raise InvoiceStateError(
                f"Cannot transition invoice {invoice_id}: already cancelled"
            )

        invoice.status = data.status
        if commit:
            db.commit()
            db.refresh(invoice)
        else:
            db.flush()
        return invoice

    @staticmethod
    def delete(db: Session, invoice_id: str, commit: bool = True) -> bool:
        invoice = InvoiceService.get_by_id(db, invoice_id)
        if not invoice:
            return False
        db.delete(invoice)
        if commit:
            db.commit()
        else:
            db.flush()
        return True
