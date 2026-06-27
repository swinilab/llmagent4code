"""
Invoice Service - Business logic for Invoice operations.
Handles invoice creation, management, and status tracking.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import InvoiceModel, InvoiceStatusEnum, OrderModel, OrderStatusEnum
from shared.models import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus


class InvoiceService:
    """Service class for Invoice business operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db_session

    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get an invoice by its unique identifier.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if invoice:
            return self._to_domain_model(invoice)
        return None

    async def get_invoice_by_order_id(self, order_id: int) -> Optional[Invoice]:
        """
        Get an invoice by its associated order ID.
        
        Args:
            order_id: The order ID
            
        Returns:
            Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.order_id == order_id)
        )
        invoice = result.scalar_one_or_none()
        
        if invoice:
            return self._to_domain_model(invoice)
        return None

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Get an invoice by its invoice number.
        
        Args:
            invoice_number: Human-readable invoice number
            
        Returns:
            Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.invoice_number == invoice_number)
        )
        invoice = result.scalar_one_or_none()
        
        if invoice:
            return self._to_domain_model(invoice)
        return None

    async def get_invoices_by_customer_id(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        """
        Get all invoices for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Invoice objects
        """
        result = await self.db.execute(
            select(InvoiceModel)
            .where(InvoiceModel.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [self._to_domain_model(i) for i in invoices]

    async def get_invoices_by_status(
        self, status: InvoiceStatus, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        """
        Get all invoices with a specific status.
        
        Args:
            status: Invoice status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Invoice objects
        """
        result = await self.db.execute(
            select(InvoiceModel)
            .where(InvoiceModel.status == InvoiceStatusEnum(status.value))
            .offset(skip)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [self._to_domain_model(i) for i in invoices]

    async def get_all_invoices(self, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Get all invoices with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Invoice objects
        """
        result = await self.db.execute(
            select(InvoiceModel)
            .offset(skip)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [self._to_domain_model(i) for i in invoices]

    async def get_invoice_count(self) -> int:
        """
        Get the total number of invoices.
        
        Returns:
            Total count of invoices
        """
        result = await self.db.execute(
            select(func.count()).select_from(InvoiceModel)
        )
        return result.scalar() or 0

    async def get_overdue_invoices(self, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Get all overdue invoices (past due date and not paid).
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of overdue Invoice objects
        """
        now = datetime.utcnow()
        result = await self.db.execute(
            select(InvoiceModel)
            .where(
                (InvoiceModel.due_date < now) &
                (InvoiceModel.status != InvoiceStatusEnum.PAID) &
                (InvoiceModel.status != InvoiceStatusEnum.CANCELLED)
            )
            .offset(skip)
            .limit(limit)
        )
        invoices = result.scalars().all()
        return [self._to_domain_model(i) for i in invoices]

    async def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """
        Create a new invoice (Accountant action).
        
        Args:
            invoice_data: InvoiceCreate object with invoice information
            
        Returns:
            Created Invoice object
        """
        # Generate invoice number
        invoice_number = await self._generate_invoice_number()
        
        # Verify order exists and is accepted
        order_result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == invoice_data.order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {invoice_data.order_id} not found")
        if order.status != OrderStatusEnum.ACCEPTED:
            raise ValueError(f"Order {invoice_data.order_id} cannot be invoiced. Current status: {order.status.value}. Order must be accepted by staff first.")
        
        # Create invoice
        invoice = InvoiceModel(
            invoice_number=invoice_number,
            order_id=invoice_data.order_id,
            customer_id=invoice_data.customer_id,
            amount=invoice_data.amount,
            status=InvoiceStatusEnum.ISSUED,
            billing_address=invoice_data.billing_address,
            due_date=invoice_data.due_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(invoice)
        await self.db.flush()  # Flush to get the invoice ID
        
        # CRITICAL FIX: Update the order with invoice_id and change status to INVOICED
        order.invoice_id = invoice.id
        order.status = OrderStatusEnum.INVOICED
        order.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return self._to_domain_model(invoice)

    async def update_invoice(
        self, invoice_id: int, invoice_data: InvoiceUpdate
    ) -> Optional[Invoice]:
        """
        Update an existing invoice.
        
        Args:
            invoice_id: The unique invoice ID
            invoice_data: InvoiceUpdate object with updated information
            
        Returns:
            Updated Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return None
        
        # Update fields if provided
        if invoice_data.status is not None:
            invoice.status = InvoiceStatusEnum(invoice_data.status.value)
        if invoice_data.amount is not None:
            invoice.amount = invoice_data.amount
        if invoice_data.due_date is not None:
            invoice.due_date = invoice_data.due_date
        if invoice_data.billing_address is not None:
            invoice.billing_address = invoice_data.billing_address
        
        invoice.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return self._to_domain_model(invoice)

    async def mark_invoice_paid(self, invoice_id: int) -> Optional[Invoice]:
        """
        Mark an invoice as paid.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Updated Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return None
        
        invoice.status = InvoiceStatusEnum.PAID
        invoice.paid_at = datetime.utcnow()
        invoice.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return self._to_domain_model(invoice)

    async def cancel_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Cancel an invoice.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Updated Invoice object if found, None otherwise
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return None
        
        if invoice.status == InvoiceStatusEnum.PAID:
            raise ValueError("Cannot cancel a paid invoice")
        
        invoice.status = InvoiceStatusEnum.CANCELLED
        invoice.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(invoice)
        
        return self._to_domain_model(invoice)

    async def check_and_update_overdue_invoices(self):
        """
        Check all issued invoices and update status to OVERDUE if past due date.
        This should be called periodically (e.g., daily).
        """
        now = datetime.utcnow()
        result = await self.db.execute(
            select(InvoiceModel)
            .where(
                (InvoiceModel.due_date < now) &
                (InvoiceModel.status == InvoiceStatusEnum.ISSUED)
            )
        )
        invoices = result.scalars().all()
        
        for invoice in invoices:
            invoice.status = InvoiceStatusEnum.OVERDUE
            invoice.updated_at = datetime.utcnow()
        
        await self.db.commit()

    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice by its ID.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return False
        
        if invoice.status == InvoiceStatusEnum.PAID:
            raise ValueError("Cannot delete a paid invoice")
        
        await self.db.delete(invoice)
        await self.db.commit()
        return True

    async def _generate_invoice_number(self) -> str:
        """
        Generate a unique invoice number.
        Format: INV-YYYYMMDD-XXXX
        
        Returns:
            Unique invoice number string
        """
        today = datetime.utcnow().strftime("%Y%m%d")
        
        # Get the count of invoices created today
        result = await self.db.execute(
            select(func.count()).select_from(InvoiceModel)
        )
        count = result.scalar() or 0
        
        invoice_number = f"INV-{today}-{count + 1:04d}"
        
        # Ensure uniqueness
        existing = await self.get_invoice_by_number(invoice_number)
        if existing:
            return await self._generate_invoice_number()
        
        return invoice_number

    def _to_domain_model(self, invoice_model: InvoiceModel) -> Invoice:
        """
        Convert SQLAlchemy model to domain model.
        
        Args:
            invoice_model: SQLAlchemy InvoiceModel object
            
        Returns:
            Domain Invoice object
        """
        return Invoice(
            id=invoice_model.id,
            invoice_number=invoice_model.invoice_number,
            order_id=invoice_model.order_id,
            customer_id=invoice_model.customer_id,
            amount=invoice_model.amount,
            status=InvoiceStatus(invoice_model.status.value),
            billing_address=invoice_model.billing_address,
            due_date=invoice_model.due_date,
            created_at=invoice_model.created_at,
            updated_at=invoice_model.updated_at,
            paid_at=invoice_model.paid_at,
        )
