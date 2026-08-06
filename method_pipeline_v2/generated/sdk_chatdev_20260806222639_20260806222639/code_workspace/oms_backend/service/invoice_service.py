"""
Invoice service layer
Business logic for invoice operations
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from oms_backend.repository import InvoiceRepository, OrderRepository, CustomerRepository
from oms_backend.repository.models import InvoiceModel, InvoiceStatus, OrderStatus
from oms_backend.domain.models import Invoice, InvoiceCreate
from oms_backend.utils.exceptions import NotFoundException, ConflictException, ValidationException
from oms_backend.utils.retry import execute_with_retry


class InvoiceService:
    """
    Service for invoice operations.
    Handles business logic and transaction boundaries.
    NFR 2.4: Transactions - ensures ACID properties for invoice creation.
    """
    
    def __init__(self, session: Session):
        """
        Initialize invoice service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
    
    def get_invoice(self, invoice_id: UUID) -> Invoice:
        """
        Get invoice by ID.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice object
            
        Raises:
            NotFoundException: If invoice not found
        """
        model = self.repository.find_by_id(invoice_id)
        if not model:
            raise NotFoundException("Invoice", str(invoice_id))
        return self._to_domain(model)
    
    def get_all_invoices(self) -> List[Invoice]:
        """
        Get all invoices.
        
        Returns:
            List of invoices
        """
        models = self.repository.find_all()
        return [self._to_domain(m) for m in models]
    
    def get_invoice_by_order(self, order_id: UUID) -> Optional[Invoice]:
        """
        Get invoice by order ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Invoice or None if not found
        """
        model = self.repository.find_by_order(order_id)
        if not model:
            return None
        return self._to_domain(model)
    
    def create_invoice(self, data: InvoiceCreate) -> Invoice:
        """
        Create a new invoice (Accountant creates invoice for accepted order).
        NFR 2.4: Transactions - validates order state and creates invoice atomically.
        
        Args:
            data: Invoice creation data
            
        Returns:
            Created invoice
            
        Raises:
            NotFoundException: If order not found
            ConflictException: If order is not in ACCEPTED state
            ValidationException: If validation fails
        """
        # Validate order exists and is in ACCEPTED state
        order = self.order_repo.find_by_id(data.orderRef)
        if not order:
            raise NotFoundException("Order", str(data.orderRef))
        
        order_status = order.status.value if hasattr(order.status, 'value') else order.status
        if order_status != OrderStatus.ACCEPTED.value:
            raise ConflictException(
                f"Order must be in ACCEPTED state to create invoice, current state: {order_status}",
                current_state=order_status,
                expected_state="ACCEPTED"
            )
        
        # Get customer for billing info snapshot
        customer = self.customer_repo.find_by_id(order.customer_ref)
        if not customer:
            raise NotFoundException("Customer", str(order.customer_ref))
        
        # Validate total amount matches order
        invoice_amount = Decimal(data.totalAmount)
        order_total = order.total_amount
        if invoice_amount != order_total:
            raise ValidationException(
                f"Invoice total {invoice_amount} must match order total {order_total}",
                field="totalAmount"
            )
        
        # Set dates
        today = date.today()
        issue_date = data.issueDate or today.strftime("%d/%m/%Y")
        
        if data.dueDate:
            due_date = data.dueDate
        else:
            # Default: issue date + 7 days
            issue_dt = datetime.strptime(issue_date, "%d/%m/%Y").date()
            due = issue_dt + timedelta(days=7)
            due_date = due.strftime("%d/%m/%Y")
        
        # Validate dueDate >= issueDate
        issue_dt = datetime.strptime(issue_date, "%d/%m/%Y").date()
        due_dt = datetime.strptime(due_date, "%d/%m/%Y").date()
        if due_dt < issue_dt:
            raise ValidationException("dueDate must be >= issueDate", field="dueDate")
        
        model_data = {
            "order_ref": data.orderRef,
            "billing_name": data.billingInfo.name,
            "billing_address": data.billingInfo.address,
            "total_amount": invoice_amount,
            "issue_date": issue_date,
            "due_date": due_date,
            "status": InvoiceStatus.ISSUED,
        }
        
        model = self.repository.create_invoice(model_data)
        self.session.flush()
        
        # Update order with invoice reference and status
        order.invoice_ref = model.id
        order.status = OrderStatus.INVOICED
        order.updated_at = datetime.utcnow()
        self.session.commit()
        
        return self._to_domain(model)
    
    def update_invoice_status(self, invoice_id: UUID, new_status: str) -> Invoice:
        """
        Update invoice status.
        
        Args:
            invoice_id: Invoice ID
            new_status: New status
            
        Returns:
            Updated invoice
        """
        model = self.repository.update_invoice(invoice_id, {"status": new_status})
        if not model:
            raise NotFoundException("Invoice", str(invoice_id))
        self.session.commit()
        return self._to_domain(model)
    
    def mark_invoice_paid(self, invoice_id: UUID) -> Invoice:
        """
        Mark invoice as paid.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice
        """
        return self.update_invoice_status(invoice_id, InvoiceStatus.PAID.value)
    
    def mark_invoice_overdue(self, invoice_id: UUID) -> Invoice:
        """
        Mark invoice as overdue.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice
        """
        return self.update_invoice_status(invoice_id, InvoiceStatus.OVERDUE.value)
    
    def cancel_invoice(self, invoice_id: UUID) -> Invoice:
        """
        Cancel invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice
        """
        return self.update_invoice_status(invoice_id, InvoiceStatus.CANCELLED.value)
    
    def _to_domain(self, model: InvoiceModel) -> Invoice:
        """Convert database model to domain model"""
        return Invoice(
            id=model.id,
            orderRef=model.order_ref,
            billingInfo={
                "name": model.billing_name,
                "address": model.billing_address,
            },
            totalAmount=f"{model.total_amount:.2f}",
            issueDate=model.issue_date,
            dueDate=model.due_date,
            status=model.status.value if hasattr(model.status, 'value') else model.status,
        )
