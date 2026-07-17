"""
Payment service for business logic operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from oms.models.payment import Payment, PaymentStatus, PaymentMethod, PaymentCreate, PaymentProcessRequest, PaymentResponse
from oms.models.order import OrderStatus
from oms.models.invoice import InvoiceStatus
from oms.repositories.payment_repository import PaymentRepository
from oms.repositories.order_repository import OrderRepository
from oms.repositories.invoice_repository import InvoiceRepository

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for Payment business logic.
    Handles payment processing, verification, and lifecycle management.
    Implements fault detection and recovery.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaymentRepository(session)
        self.order_repository = OrderRepository(session)
        self.invoice_repository = InvoiceRepository(session)
    
    async def get_payment(self, payment_id: int) -> Optional[PaymentResponse]:
        """Get a payment by ID."""
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            return None
        return PaymentResponse.model_validate(payment)
    
    async def get_payment_by_order_id(self, order_id: int) -> Optional[PaymentResponse]:
        """Get a payment by order ID."""
        payment = await self.repository.get_by_order_id(order_id)
        if not payment:
            return None
        return PaymentResponse.model_validate(payment)
    
    async def get_payments_by_status(self, status: PaymentStatus, skip: int = 0, limit: int = 100) -> List[PaymentResponse]:
        """Get payments by status."""
        payments = await self.repository.get_by_status(status, skip=skip, limit=limit)
        return [PaymentResponse.model_validate(p) for p in payments]
    
    async def get_all_payments(self, skip: int = 0, limit: int = 100) -> List[PaymentResponse]:
        """Get all payments with pagination."""
        payments = await self.repository.get_all(skip=skip, limit=limit)
        return [PaymentResponse.model_validate(p) for p in payments]
    
    async def create_payment(self, payment_data: PaymentCreate) -> PaymentResponse:
        """
        Create a payment for an order (Customer workflow step 4).
        """
        order = await self.order_repository.get_by_id(payment_data.order_id)
        if not order:
            raise ValueError(f"Order {payment_data.order_id} not found")
        
        if order.status not in [OrderStatus.PAYMENT_PENDING, OrderStatus.INVOICED]:
            raise ValueError(f"Order {payment_data.order_id} is not ready for payment")
        
        existing_payment = await self.repository.get_by_order_id(payment_data.order_id)
        if existing_payment:
            raise ValueError(f"Payment already exists for order {payment_data.order_id}")
        
        # Auto-link invoice if not provided
        invoice_id = payment_data.invoice_id
        if not invoice_id:
            invoice = await self.invoice_repository.get_by_order_id(payment_data.order_id)
            if invoice:
                invoice_id = invoice.id
        
        # Create payment with invoice_id
        payment = await self.repository.create(
            PaymentCreate(
                order_id=payment_data.order_id,
                invoice_id=invoice_id,
                amount=payment_data.amount,
                currency=payment_data.currency,
                method=payment_data.method,
                notes=payment_data.notes,
            )
        )
        return PaymentResponse.model_validate(payment)
    
    async def process_payment(self, payment_id: int, transaction_id: Optional[str] = None) -> Optional[PaymentResponse]:
        """
        Process a payment (simulate payment gateway).
        Implements fault detection and recovery.
        """
        try:
            payment = await self.repository.process(payment_id, transaction_id)
            if not payment:
                return None
            
            logger.info(f"Payment {payment_id} is processing")
            return PaymentResponse.model_validate(payment)
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            await self.repository.fail(payment_id, str(e))
            raise
    
    async def verify_payment(self, payment_id: int, confirmed: bool, notes: Optional[str] = None) -> Optional[PaymentResponse]:
        """
        Verify a payment (Accountant workflow step 5).
        """
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            return None
        
        if confirmed:
            payment = await self.repository.complete(payment_id)
            
            invoice = await self.invoice_repository.get_by_order_id(payment.order_id)
            if invoice:
                await self.invoice_repository.update_status(invoice.id, InvoiceStatus.PAID)
            
            order = await self.order_repository.get_by_id(payment.order_id)
            if order:
                order.status = OrderStatus.PAID
                await self.session.flush()
            
            logger.info(f"Payment {payment_id} verified and completed")
        else:
            payment = await self.repository.fail(payment_id, notes)
            logger.warning(f"Payment {payment_id} verification failed")
        
        return PaymentResponse.model_validate(payment)
    
    async def refund_payment(self, payment_id: int, notes: Optional[str] = None) -> Optional[PaymentResponse]:
        """Refund a payment."""
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            return None
        
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Payment {payment_id} must be COMPLETED before refund")
        
        payment = await self.repository.update(payment_id, status=PaymentStatus.REFUNDED, notes=notes)
        
        order = await self.order_repository.get_by_id(payment.order_id)
        if order:
            order.status = OrderStatus.CANCELLED
            await self.session.flush()
        
        return PaymentResponse.model_validate(payment)
    
    async def update_payment(self, payment_id: int, **kwargs) -> Optional[PaymentResponse]:
        """Update a payment."""
        payment = await self.repository.update(payment_id, **kwargs)
        if not payment:
            return None
        return PaymentResponse.model_validate(payment)
    
    async def delete_payment(self, payment_id: int) -> bool:
        """Delete a payment."""
        return await self.repository.delete(payment_id)
    
    async def get_payment_count(self) -> int:
        """Get total number of payments."""
        return await self.repository.count()
