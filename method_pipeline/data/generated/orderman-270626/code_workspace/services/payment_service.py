"""
Payment Service - Business logic for Payment operations.
Handles payment processing, tracking, and status management.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import (
    PaymentModel,
    PaymentStatusEnum,
    InvoiceModel,
    InvoiceStatusEnum,
    OrderModel,
    OrderStatusEnum,
)
from shared.models import Payment, PaymentCreate, PaymentUpdate, PaymentStatus


class PaymentService:
    """Service class for Payment business operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the service with a database session."""
        self.db = db_session

    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """
        Get a payment by its unique identifier.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            Payment object if found, None otherwise
        """
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            return self._to_domain_model(payment)
        return None

    async def get_payments_by_invoice_id(
        self, invoice_id: int, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        """
        Get all payments for a specific invoice.
        
        Args:
            invoice_id: The invoice ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Payment objects
        """
        result = await self.db.execute(
            select(PaymentModel)
            .where(PaymentModel.invoice_id == invoice_id)
            .offset(skip)
            .limit(limit)
        )
        payments = result.scalars().all()
        return [self._to_domain_model(p) for p in payments]

    async def get_payments_by_customer_id(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        """
        Get all payments for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Payment objects
        """
        result = await self.db.execute(
            select(PaymentModel)
            .where(PaymentModel.customer_id == customer_id)
            .offset(skip)
            .limit(limit)
        )
        payments = result.scalars().all()
        return [self._to_domain_model(p) for p in payments]

    async def get_payments_by_status(
        self, status: PaymentStatus, skip: int = 0, limit: int = 100
    ) -> List[Payment]:
        """
        Get all payments with a specific status.
        
        Args:
            status: Payment status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Payment objects
        """
        result = await self.db.execute(
            select(PaymentModel)
            .where(PaymentModel.status == PaymentStatusEnum(status.value))
            .offset(skip)
            .limit(limit)
        )
        payments = result.scalars().all()
        return [self._to_domain_model(p) for p in payments]

    async def get_all_payments(self, skip: int = 0, limit: int = 100) -> List[Payment]:
        """
        Get all payments with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of Payment objects
        """
        result = await self.db.execute(
            select(PaymentModel)
            .offset(skip)
            .limit(limit)
        )
        payments = result.scalars().all()
        return [self._to_domain_model(p) for p in payments]

    async def get_payment_count(self) -> int:
        """
        Get the total number of payments.
        
        Returns:
            Total count of payments
        """
        result = await self.db.execute(
            select(func.count()).select_from(PaymentModel)
        )
        return result.scalar() or 0

    async def create_payment(self, payment_data: PaymentCreate) -> Payment:
        """
        Create a new payment (Customer action on issued invoice).
        
        Args:
            payment_data: PaymentCreate object with payment information
            
        Returns:
            Created Payment object
        """
        # Verify invoice exists and is issued
        invoice_result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == payment_data.invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        
        if not invoice:
            raise ValueError(f"Invoice {payment_data.invoice_id} not found")
        
        if invoice.status not in [InvoiceStatusEnum.ISSUED, InvoiceStatusEnum.OVERDUE]:
            raise ValueError(f"Invoice {payment_data.invoice_id} cannot be paid. Current status: {invoice.status.value}")
        
        # Verify payment amount matches invoice amount
        if payment_data.amount != invoice.amount:
            raise ValueError(
                f"Payment amount {payment_data.amount} does not match invoice amount {invoice.amount}"
            )
        
        # Create payment
        payment = PaymentModel(
            invoice_id=payment_data.invoice_id,
            customer_id=payment_data.customer_id,
            amount=payment_data.amount,
            status=PaymentStatusEnum.PROCESSING,
            payment_method=payment_data.payment_method,
            transaction_id=payment_data.transaction_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(payment)
        await self.db.flush()  # Get the payment ID
        
        # Process the payment
        await self._process_payment(payment, invoice)
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return self._to_domain_model(payment)

    async def _process_payment(self, payment: PaymentModel, invoice: InvoiceModel):
        """
        Process a payment and update related entities.
        This simulates payment processing logic.
        
        Args:
            payment: PaymentModel to process
            invoice: Associated InvoiceModel
        """
        # Simulate payment processing (in real system, this would call payment gateway)
        payment.status = PaymentStatusEnum.COMPLETED
        payment.processed_at = datetime.utcnow()
        payment.updated_at = datetime.utcnow()
        
        # Update invoice status
        invoice.status = InvoiceStatusEnum.PAID
        invoice.paid_at = datetime.utcnow()
        invoice.updated_at = datetime.utcnow()
        
        # Update order status
        order_result = await self.db.execute(
            select(OrderModel).where(OrderModel.id == invoice.order_id)
        )
        order = order_result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order {invoice.order_id} not found for invoice {invoice.id}")
        
        if order.status not in [OrderStatusEnum.INVOICED, OrderStatusEnum.ACCEPTED]:
            raise ValueError(f"Order {order.id} cannot be marked as paid. Current status: {order.status.value}")
        
        order.status = OrderStatusEnum.PAID
        order.updated_at = datetime.utcnow()

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
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        # Update fields if provided
        if payment_data.status is not None:
            payment.status = PaymentStatusEnum(payment_data.status.value)
        if payment_data.amount is not None:
            payment.amount = payment_data.amount
        if payment_data.transaction_id is not None:
            payment.transaction_id = payment_data.transaction_id
        
        payment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return self._to_domain_model(payment)

    async def refund_payment(self, payment_id: int) -> Optional[Payment]:
        """
        Refund a payment.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            Updated Payment object if found, None otherwise
        """
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        if payment.status != PaymentStatusEnum.COMPLETED:
            raise ValueError("Only completed payments can be refunded")
        
        payment.status = PaymentStatusEnum.REFUNDED
        payment.updated_at = datetime.utcnow()
        
        # Update invoice status back to issued
        invoice_result = await self.db.execute(
            select(InvoiceModel).where(InvoiceModel.id == payment.invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        
        if invoice:
            invoice.status = InvoiceStatusEnum.ISSUED
            invoice.paid_at = None
            invoice.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return self._to_domain_model(payment)

    async def fail_payment(self, payment_id: int, reason: str = None) -> Optional[Payment]:
        """
        Mark a payment as failed.
        
        Args:
            payment_id: The unique payment ID
            reason: Optional reason for failure
            
        Returns:
            Updated Payment object if found, None otherwise
        """
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        payment.status = PaymentStatusEnum.FAILED
        payment.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return self._to_domain_model(payment)

    async def delete_payment(self, payment_id: int) -> bool:
        """
        Delete a payment by its ID.
        
        Args:
            payment_id: The unique payment ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        result = await self.db.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if not payment:
            return False
        
        if payment.status == PaymentStatusEnum.COMPLETED:
            raise ValueError("Cannot delete a completed payment")
        
        await self.db.delete(payment)
        await self.db.commit()
        return True

    def _to_domain_model(self, payment_model: PaymentModel) -> Payment:
        """
        Convert SQLAlchemy model to domain model.
        
        Args:
            payment_model: SQLAlchemy PaymentModel object
            
        Returns:
            Domain Payment object
        """
        return Payment(
            id=payment_model.id,
            invoice_id=payment_model.invoice_id,
            customer_id=payment_model.customer_id,
            amount=payment_model.amount,
            status=PaymentStatus(payment_model.status.value),
            payment_method=payment_model.payment_method,
            transaction_id=payment_model.transaction_id,
            created_at=payment_model.created_at,
            updated_at=payment_model.updated_at,
            processed_at=payment_model.processed_at,
        )
