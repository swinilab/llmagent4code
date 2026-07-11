"""
Invoice service for invoice-related business logic.

Handles invoice creation, management, and status tracking.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Invoice, InvoiceStatus, OrderStatus
from oms.models.schemas import InvoiceCreate, InvoiceResponse
from oms.repositories.invoice_repository import InvoiceRepository
from oms.repositories.order_repository import OrderRepository


class InvoiceService:
    """
    Service for managing invoice operations.
    
    Handles the invoice workflow:
    1. Accountant creates invoice for accepted order
    2. Invoice is issued to customer
    3. Invoice status updated when payment received
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize invoice service.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.repository = InvoiceRepository(session)
        self.order_repository = OrderRepository(session)
        self.session = session
    
    def _generate_invoice_number(self) -> str:
        """
        Generate a unique invoice number.
        
        Returns:
            Unique invoice number in format INV-YYYYMMDD-XXXX
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        import random
        suffix = random.randint(1000, 9999)
        return f"INV-{timestamp}-{suffix}"
    
    async def create_invoice(self, invoice_data: InvoiceCreate) -> InvoiceResponse:
        """
        Create a new invoice for an order (Accountant action).
        
        Args:
            invoice_data: Invoice creation data
            
        Returns:
            Created invoice response
            
        Raises:
            ValueError: If order not found or not in correct status
        """
        order = await self.order_repository.get(invoice_data.order_id)
        if order is None:
            raise ValueError(f"Order {invoice_data.order_id} not found")
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(
                f"Order {invoice_data.order_id} is not in ACCEPTED status. "
                f"Current status: {order.status.value}"
            )
        
        existing_invoice = await self.repository.get_by_order(invoice_data.order_id)
        if existing_invoice:
            raise ValueError(f"Invoice already exists for order {invoice_data.order_id}")
        
        subtotal = order.total_amount
        tax_amount = subtotal * invoice_data.tax_rate
        total_amount = subtotal + tax_amount
        
        invoice = Invoice(
            order_id=invoice_data.order_id,
            invoice_number=self._generate_invoice_number(),
            billing_name=invoice_data.billing_name,
            billing_address=invoice_data.billing_address,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            issue_date=datetime.utcnow(),
            due_date=invoice_data.due_date,
            status=InvoiceStatus.ISSUED,
        )
        
        created = await self.repository.create(invoice)
        
        order.status = OrderStatus.INVOICED
        order.invoice_id = created.id
        await self.order_repository.update(order)
        
        return InvoiceResponse.model_validate(created)
    
    async def get_invoice(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """
        Get invoice by ID.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice response or None if not found
        """
        invoice = await self.repository.get(invoice_id)
        if invoice is None:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def get_invoice_by_order(self, order_id: int) -> Optional[InvoiceResponse]:
        """
        Get invoice by order ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Invoice response or None if not found
        """
        invoice = await self.repository.get_by_order(order_id)
        if invoice is None:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def get_invoice_by_number(
        self, invoice_number: str
    ) -> Optional[InvoiceResponse]:
        """
        Get invoice by invoice number.
        
        Args:
            invoice_number: Unique invoice number
            
        Returns:
            Invoice response or None if not found
        """
        invoice = await self.repository.get_by_invoice_number(invoice_number)
        if invoice is None:
            return None
        return InvoiceResponse.model_validate(invoice)
    
    async def get_all_invoices(
        self, limit: int = 100, offset: int = 0
    ) -> List[InvoiceResponse]:
        """
        Get all invoices with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of invoice responses
        """
        invoices = await self.repository.get_all(limit=limit, offset=offset)
        return [InvoiceResponse.model_validate(i) for i in invoices]
    
    async def get_invoices_by_status(
        self, status: InvoiceStatus, limit: int = 100, offset: int = 0
    ) -> List[InvoiceResponse]:
        """
        Get invoices by status.
        
        Args:
            status: Invoice status to filter by
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of invoice responses
        """
        invoices = await self.repository.get_invoices_by_status(
            status, limit=limit, offset=offset
        )
        return [InvoiceResponse.model_validate(i) for i in invoices]
    
    async def mark_invoice_paid(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """
        Mark an invoice as paid.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice response or None if not found
        """
        invoice = await self.repository.get(invoice_id)
        if invoice is None:
            return None
        
        invoice.status = InvoiceStatus.PAID
        updated = await self.repository.update(invoice)
        return InvoiceResponse.model_validate(updated)
    
    async def mark_invoice_overdue(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """
        Mark an invoice as overdue.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice response or None if not found
        """
        invoice = await self.repository.get(invoice_id)
        if invoice is None:
            return None
        
        invoice.status = InvoiceStatus.OVERDUE
        updated = await self.repository.update(invoice)
        return InvoiceResponse.model_validate(updated)
    
    async def cancel_invoice(self, invoice_id: int) -> Optional[InvoiceResponse]:
        """
        Cancel an invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice response or None if not found
            
        Raises:
            ValueError: If invoice is already paid
        """
        invoice = await self.repository.get(invoice_id)
        if invoice is None:
            return None
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Cannot cancel a paid invoice")
        
        invoice.status = InvoiceStatus.CANCELLED
        
        order = await self.order_repository.get(invoice.order_id)
        if order:
            order.status = OrderStatus.ACCEPTED
            order.invoice_id = None
            await self.order_repository.update(order)
        
        updated = await self.repository.update(invoice)
        return InvoiceResponse.model_validate(updated)
    
    async def get_overdue_invoices(self, limit: int = 100) -> List[InvoiceResponse]:
        """
        Get all overdue invoices.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of overdue invoice responses
        """
        invoices = await self.repository.get_overdue_invoices(
            datetime.utcnow(), limit=limit
        )
        return [InvoiceResponse.model_validate(i) for i in invoices]
    
    async def check_and_update_overdue(self) -> int:
        """
        Check all issued invoices and update overdue status.
        
        Returns:
            Number of invoices updated to overdue
        """
        current_date = datetime.utcnow()
        invoices = await self.repository.get_overdue_invoices(
            current_date, limit=1000
        )
        
        updated_count = 0
        for invoice in invoices:
            if invoice.status == InvoiceStatus.ISSUED:
                invoice.status = InvoiceStatus.OVERDUE
                await self.repository.update(invoice)
                updated_count += 1
        
        return updated_count
    
    async def get_total_invoiced_amount(self) -> float:
        """
        Get total invoiced amount.
        
        Returns:
            Total invoiced amount
        """
        return await self.repository.get_total_invoiced_amount()
    
    async def get_total_paid_amount(self) -> float:
        """
        Get total paid invoice amount.
        
        Returns:
            Total paid amount
        """
        return await self.repository.get_total_paid_amount()
