"""
Invoice Controller - Handles HTTP request/response for Invoice operations.
Coordinates between routes and services.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceListResponse,
    InvoiceStatus,
)
from services.invoice_service import InvoiceService


class InvoiceController:
    """Controller class for Invoice HTTP operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the controller with a database session."""
        self.service = InvoiceService(db_session)

    async def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Get a single invoice by ID.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Invoice object if found, None otherwise
        """
        return await self.service.get_invoice_by_id(invoice_id)

    async def get_invoice_by_order_id(self, order_id: int) -> Optional[Invoice]:
        """
        Get an invoice by order ID.
        
        Args:
            order_id: The order ID
            
        Returns:
            Invoice object if found, None otherwise
        """
        return await self.service.get_invoice_by_order_id(order_id)

    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Get an invoice by invoice number.
        
        Args:
            invoice_number: Human-readable invoice number
            
        Returns:
            Invoice object if found, None otherwise
        """
        return await self.service.get_invoice_by_number(invoice_number)

    async def get_invoices_by_customer(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> InvoiceListResponse:
        """
        Get all invoices for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            InvoiceListResponse with invoices and total count
        """
        invoices = await self.service.get_invoices_by_customer_id(
            customer_id=customer_id, skip=skip, limit=limit
        )
        return InvoiceListResponse(invoices=invoices, total=len(invoices))

    async def get_invoices_by_status(
        self, status: InvoiceStatus, skip: int = 0, limit: int = 100
    ) -> InvoiceListResponse:
        """
        Get all invoices with a specific status.
        
        Args:
            status: Invoice status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            InvoiceListResponse with invoices and total count
        """
        invoices = await self.service.get_invoices_by_status(
            status=status, skip=skip, limit=limit
        )
        return InvoiceListResponse(invoices=invoices, total=len(invoices))

    async def get_all_invoices(
        self, skip: int = 0, limit: int = 100
    ) -> InvoiceListResponse:
        """
        Get all invoices with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            InvoiceListResponse with invoices and total count
        """
        invoices = await self.service.get_all_invoices(skip=skip, limit=limit)
        total = await self.service.get_invoice_count()
        return InvoiceListResponse(invoices=invoices, total=total)

    async def get_overdue_invoices(
        self, skip: int = 0, limit: int = 100
    ) -> InvoiceListResponse:
        """
        Get all overdue invoices.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            InvoiceListResponse with overdue invoices and total count
        """
        invoices = await self.service.get_overdue_invoices(skip=skip, limit=limit)
        return InvoiceListResponse(invoices=invoices, total=len(invoices))

    async def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """
        Create a new invoice (Accountant action).
        
        Args:
            invoice_data: InvoiceCreate object with invoice information
            
        Returns:
            Created Invoice object
        """
        return await self.service.create_invoice(invoice_data)

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
        return await self.service.update_invoice(invoice_id, invoice_data)

    async def mark_invoice_paid(self, invoice_id: int) -> Optional[Invoice]:
        """
        Mark an invoice as paid.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Updated Invoice object if found, None otherwise
        """
        return await self.service.mark_invoice_paid(invoice_id)

    async def cancel_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """
        Cancel an invoice.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            Updated Invoice object if found, None otherwise
        """
        return await self.service.cancel_invoice(invoice_id)

    async def delete_invoice(self, invoice_id: int) -> bool:
        """
        Delete an invoice.
        
        Args:
            invoice_id: The unique invoice ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return await self.service.delete_invoice(invoice_id)

    async def check_overdue_invoices(self) -> dict:
        """
        Check and update overdue invoices.
        
        Returns:
            Dictionary with count of updated invoices
        """
        before_count = len(await self.service.get_overdue_invoices(limit=1000))
        await self.service.check_and_update_overdue_invoices()
        after_count = len(await self.service.get_overdue_invoices(limit=1000))
        return {"updated_count": after_count - before_count}
