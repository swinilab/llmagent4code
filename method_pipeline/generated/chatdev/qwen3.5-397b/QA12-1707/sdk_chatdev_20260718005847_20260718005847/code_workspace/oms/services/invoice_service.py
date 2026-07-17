"""
Invoice service for business logic operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from oms.models.invoice import Invoice, InvoiceStatus, InvoiceCreate, InvoiceResponse
from oms.models.order import OrderStatus
from oms.repositories.invoice_repository import InvoiceRepository
from oms.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service for Invoice business logic.
    Handles invoice creation, issuance, and lifecycle management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = InvoiceRepository(session)
        self.order_repository = OrderRepository(session)
    
    async def get_invoice(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """Get an invoice by ID."""
        invoice = await self.repository.get_by_id(invoice_id)
        if not invoice:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def get_invoice_by_order_id(self, order_id: int) -> Optional[InvoiceResponse]:
        """Get an invoice by order ID."""
        invoice = await self.repository.get_by_order_id(order_id)
        if not invoice:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def get_invoices_by_status(self, status: InvoiceStatus, skip: int = 0, limit: int = 100) -> List[InvoiceResponse]:
        """Get invoices by status."""
        invoices = await self.repository.get_by_status(status, skip=skip, limit=limit)
        return [InvoiceResponse.model_validate(i) for i in invoices]
    
    async def get_all_invoices(self, skip: int = 0, limit: int = 100) -> List[InvoiceResponse]:
        """Get all invoices with pagination."""
        invoices = await self.repository.get_all(skip=skip, limit=limit)
        return [InvoiceResponse.model_validate(i) for i in invoices]
    
    async def create_invoice(self, invoice_data: InvoiceCreate) -> InvoiceResponse:
        """
        Create an invoice for an accepted order (Accountant workflow step 3).
        """
        order = await self.order_repository.get_by_id(invoice_data.order_id)
        if not order:
            raise ValueError(f"Order {invoice_data.order_id} not found")
        
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(f"Order {invoice_data.order_id} must be ACCEPTED before invoicing")
        
        subtotal = float(order.total_amount)
        tax_amount = subtotal * float(invoice_data.tax_rate)
        total = subtotal + tax_amount
        
        invoice = await self.repository.create(invoice_data, subtotal, total)
        
        order.status = OrderStatus.INVOICED
        order.invoice_id = invoice.id
        await self.session.flush()
        
        return InvoiceResponse.model_validate(invoice)
    
    async def issue_invoice(self, invoice_id: int, issue_date: Optional[datetime] = None,
                           due_date: Optional[datetime] = None) -> Optional[InvoiceResponse]:
        """Issue an invoice."""
        invoice = await self.repository.issue(invoice_id, issue_date, due_date)
        if not invoice:
            return None
        
        order = await self.order_repository.get_by_id(invoice.order_id)
        if order:
            order.status = OrderStatus.PAYMENT_PENDING
            await self.session.flush()
        
        return InvoiceResponse.model_validate(invoice)
    
    async def mark_invoice_paid(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """Mark invoice as paid."""
        invoice = await self.repository.update_status(invoice_id, InvoiceStatus.PAID)
        if not invoice:
            return None
        
        order = await self.order_repository.get_by_id(invoice.order_id)
        if order:
            order.status = OrderStatus.PAID
            await self.session.flush()
        
        return InvoiceResponse.model_validate(invoice)
    
    async def cancel_invoice(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """Cancel an invoice."""
        invoice = await self.repository.update_status(invoice_id, InvoiceStatus.CANCELLED)
        if not invoice:
            return None
        
        order = await self.order_repository.get_by_id(invoice.order_id)
        if order and order.status in [OrderStatus.INVOICED, OrderStatus.PAYMENT_PENDING]:
            order.status = OrderStatus.ACCEPTED
            await self.session.flush()
        
        return InvoiceResponse.model_validate(invoice)
    
    async def update_invoice(self, invoice_id: int, **kwargs) -> Optional[InvoiceResponse]:
        """Update an invoice."""
        invoice = await self.repository.update(invoice_id, **kwargs)
        if not invoice:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def delete_invoice(self, invoice_id: int) -> bool:
        """Delete an invoice."""
        return await self.repository.delete(invoice_id)
    
    async def get_invoice_count(self) -> int:
        """Get total number of invoices."""
        return await self.repository.count()
