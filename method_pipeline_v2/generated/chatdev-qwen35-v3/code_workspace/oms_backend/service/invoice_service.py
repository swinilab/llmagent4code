"""
Invoice service with business logic
Implements NFR 2.4 (transactions) and date validation
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from oms_backend.repository.invoice_repository import InvoiceRepository
from oms_backend.repository.order_repository import OrderRepository
from oms_backend.repository.customer_repository import CustomerRepository
from oms_backend.domain.models import Invoice, InvoiceStatus, OrderStatus, Customer
from oms_backend.domain.schemas import InvoiceCreate


def parse_date(date_str: str) -> datetime:
    """Parse dd/MM/yyyy date string"""
    day, month, year = map(int, date_str.split('/'))
    return datetime(year=year, month=month, day=day)


def format_date(dt: datetime) -> str:
    """Format datetime to dd/MM/yyyy"""
    return dt.strftime("%d/%m/%Y")


class InvoiceService:
    """Service for Invoice business logic with transactional guarantees"""
    
    def __init__(self, session: AsyncSession):
        self.repository = InvoiceRepository(session)
        self.order_repo = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.session = session
    
    async def create_invoice(self, data: InvoiceCreate) -> Invoice:
        """Create a new invoice with full validation (NFR 2.4 - ACID transactions)"""
        # Validate order exists and is ACCEPTED
        order = await self.order_repo.get_by_id(data.orderRef)
        if not order:
            raise ValueError(f"Order not found: {data.orderRef}")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(f"Order must be ACCEPTED, current status: {order.status}")
        
        # Validate total amount matches order total
        if float(data.totalAmount) != float(order.total_amount):
            raise ValueError(
                f"Invoice total {data.totalAmount} must match order total {order.total_amount}"
            )
        
        # Validate dates
        issue_date = parse_date(data.issueDate)
        due_date = parse_date(data.dueDate)
        
        if due_date < issue_date:
            raise ValueError("Due date must be >= issue date")
        
        # Get customer for billing info validation
        customer = await self.customer_repo.get_by_id(order.customer_ref)
        if not customer:
            raise ValueError(f"Customer not found: {order.customer_ref}")
        
        invoice = await self.repository.create(data)
        
        # Update order with invoice reference
        await self.order_repo.set_invoice_ref(data.orderRef, invoice.id)
        
        return invoice
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID with cache (NFR 1.2)"""
        from oms_backend.repository.base import db
        cache_key = f"invoice:{invoice_id}"
        cached = db.get_cached(cache_key)
        if cached:
            return cached
        
        invoice = await self.repository.get_by_id(invoice_id)
        if invoice:
            db.set_cached(cache_key, invoice)
        return invoice
    
    async def get_invoice_by_order(self, order_ref: str) -> Optional[Invoice]:
        """Get invoice by order reference"""
        return await self.repository.get_by_order_ref(order_ref)
    
    async def get_all_invoices(self, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """Get all invoices"""
        return await self.repository.get_all(limit, offset)
    
    async def mark_invoice_paid(self, invoice_id: str) -> Optional[Invoice]:
        """Mark invoice as paid (ISSUED -> PAID)"""
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.ISSUED:
            raise ValueError(f"Invoice must be ISSUED, current status: {invoice.status}")
        return await self.repository.update_status(invoice_id, InvoiceStatus.PAID)
    
    async def mark_invoice_overdue(self, invoice_id: str) -> Optional[Invoice]:
        """Mark invoice as overdue (ISSUED -> OVERDUE)"""
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            return None
        if invoice.status != InvoiceStatus.ISSUED:
            raise ValueError(f"Invoice must be ISSUED, current status: {invoice.status}")
        return await self.repository.update_status(invoice_id, InvoiceStatus.OVERDUE)
    
    async def cancel_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Cancel invoice (ISSUED/OVERDUE -> CANCELLED)"""
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            return None
        if invoice.status not in [InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE]:
            raise ValueError(f"Invoice must be ISSUED or OVERDUE, current status: {invoice.status}")
        return await self.repository.update_status(invoice_id, InvoiceStatus.CANCELLED)
