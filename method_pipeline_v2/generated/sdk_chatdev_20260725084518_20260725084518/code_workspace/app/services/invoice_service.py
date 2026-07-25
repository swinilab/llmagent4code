"""
Invoice service with business logic
"""
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.customer_repository import CustomerRepository
from app.models.invoice import Invoice, InvoiceStatus, BillingInfo
from app.models.order import OrderStatus
from app.db.tables import InvoiceTable


class InvoiceValidationError(Exception):
    """Raised when invoice validation fails"""
    pass


class InvoiceTransitionError(Exception):
    """Raised when invalid state transition is attempted"""
    pass


class InvoiceService:
    """Service layer for Invoice operations"""
    
    def __init__(self, session: AsyncSession):
        self.repository = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
    
    async def create_invoice(
        self,
        order_ref: str,
        issue_date: str = None,
        due_date: str = None,
    ) -> Invoice:
        """Create a new invoice for an order"""
        # Validate order exists and is ACCEPTED
        order = await self.order_repo.get_by_id(order_ref)
        if not order:
            raise InvoiceValidationError(f"Order {order_ref} not found")
        
        if order.status != OrderStatus.ACCEPTED:
            raise InvoiceValidationError(
                f"Cannot create invoice for order in status {order.status}. Order must be ACCEPTED."
            )
        
        # Check if invoice already exists
        existing = await self.repository.get_by_order_ref(order_ref)
        if existing:
            raise InvoiceValidationError(f"Invoice already exists for order {order_ref}")
        
        # Get customer for billing info
        customer = await self.customer_repo.get_by_id(order.customer_ref)
        if not customer:
            raise InvoiceValidationError(f"Customer {order.customer_ref} not found")
        
        # Set dates
        if not issue_date:
            now = datetime.utcnow()
            issue_date = now.strftime("%d/%m/%Y")
        
        if not due_date:
            # Default due date is issue date + 7 days
            from datetime import timedelta
            issue_dt = datetime.strptime(issue_date, "%d/%m/%Y")
            due_dt = issue_dt + timedelta(days=7)
            due_date = due_dt.strftime("%d/%m/%Y")
        
        entity = await self.repository.create_invoice(
            order_ref=order_ref,
            billing_name=customer.name,
            billing_address=customer.address,
            total_amount=order.total_amount,
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.ISSUED,
        )
        
        # Update order status to INVOICED and set invoice ref
        await self.order_repo.update_status(order_ref, OrderStatus.INVOICED)
        await self.order_repo.set_invoice_ref(order_ref, entity.id)
        
        return self._to_model(entity)
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        entity = await self.repository.get_by_id(invoice_id)
        return self._to_model(entity) if entity else None
    
    async def get_invoice_by_order(self, order_ref: str) -> Optional[Invoice]:
        """Get invoice by order reference"""
        entity = await self.repository.get_by_order_ref(order_ref)
        return self._to_model(entity) if entity else None
    
    async def get_all_invoices(self, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """Get all invoices"""
        entities = await self.repository.get_all(limit, offset)
        return [self._to_model(e) for e in entities]
    
    async def cancel_invoice(self, invoice_id: str) -> Invoice:
        """Cancel invoice"""
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            raise InvoiceValidationError(f"Invoice {invoice_id} not found")
        
        if invoice.status not in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            raise InvoiceTransitionError(
                f"Cannot cancel invoice in status {invoice.status}"
            )
        
        entity = await self.repository.update_status(invoice_id, InvoiceStatus.CANCELLED)
        return self._to_model(entity)
    
    def _to_model(self, entity: InvoiceTable) -> Invoice:
        """Convert table entity to domain model"""
        return Invoice(
            id=entity.id,
            orderRef=entity.order_ref,
            billingInfo=BillingInfo(
                name=entity.billing_name,
                address=entity.billing_address,
            ),
            totalAmount=Decimal(str(entity.total_amount)),
            issueDate=entity.issue_date,
            dueDate=entity.due_date,
            status=entity.status,
        )
