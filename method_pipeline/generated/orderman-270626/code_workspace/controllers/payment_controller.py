"""
Payment Controller - Handles HTTP request/response for Payment operations.
Coordinates between routes and services.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Payment,
    PaymentCreate,
    PaymentUpdate,
    PaymentListResponse,
    PaymentStatus,
)
from services.payment_service import PaymentService


class PaymentController:
    """Controller class for Payment HTTP operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the controller with a database session."""
        self.service = PaymentService(db_session)

    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        """
        Get a single payment by ID.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            Payment object if found, None otherwise
        """
        return await self.service.get_payment_by_id(payment_id)

    async def get_payments_by_invoice(
        self, invoice_id: int, skip: int = 0, limit: int = 100
    ) -> PaymentListResponse:
        """
        Get all payments for a specific invoice.
        
        Args:
            invoice_id: The invoice ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            PaymentListResponse with payments and total count
        """
        payments = await self.service.get_payments_by_invoice_id(
            invoice_id=invoice_id, skip=skip, limit=limit
        )
        return PaymentListResponse(payments=payments, total=len(payments))

    async def get_payments_by_customer(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> PaymentListResponse:
        """
        Get all payments for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            PaymentListResponse with payments and total count
        """
        payments = await self.service.get_payments_by_customer_id(
            customer_id=customer_id, skip=skip, limit=limit
        )
        return PaymentListResponse(payments=payments, total=len(payments))

    async def get_payments_by_status(
        self, status: PaymentStatus, skip: int = 0, limit: int = 100
    ) -> PaymentListResponse:
        """
        Get all payments with a specific status.
        
        Args:
            status: Payment status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            PaymentListResponse with payments and total count
        """
        payments = await self.service.get_payments_by_status(
            status=status, skip=skip, limit=limit
        )
        return PaymentListResponse(payments=payments, total=len(payments))

    async def get_all_payments(
        self, skip: int = 0, limit: int = 100
    ) -> PaymentListResponse:
        """
        Get all payments with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            PaymentListResponse with payments and total count
        """
        payments = await self.service.get_all_payments(skip=skip, limit=limit)
        total = await self.service.get_payment_count()
        return PaymentListResponse(payments=payments, total=total)

    async def create_payment(self, payment_data: PaymentCreate) -> Payment:
        """
        Create a new payment (Customer action on issued invoice).
        
        Args:
            payment_data: PaymentCreate object with payment information
            
        Returns:
            Created Payment object
        """
        return await self.service.create_payment(payment_data)

    async def update_payment(
        self, payment_id: int, payment_data: PaymentUpdate
    ) -> Optional[Payment]:
        """
        Update an existing payment.
        
        Args:
            payment_id: The unique payment ID
            payment_data: PaymentUpdate object with updated information
            
        Returns:
            Updated Payment object if found, None otherwise
        """
        return await self.service.update_payment(payment_id, payment_data)

    async def refund_payment(self, payment_id: int) -> Optional[Payment]:
        """
        Refund a payment.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            Updated Payment object if found, None otherwise
        """
        return await self.service.refund_payment(payment_id)

    async def fail_payment(self, payment_id: int, reason: str = None) -> Optional[Payment]:
        """
        Mark a payment as failed.
        
        Args:
            payment_id: The unique payment ID
            reason: Optional reason for failure
            
        Returns:
            Updated Payment object if found, None otherwise
        """
        return await self.service.fail_payment(payment_id, reason)

    async def delete_payment(self, payment_id: int) -> bool:
        """
        Delete a payment.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return await self.service.delete_payment(payment_id)
