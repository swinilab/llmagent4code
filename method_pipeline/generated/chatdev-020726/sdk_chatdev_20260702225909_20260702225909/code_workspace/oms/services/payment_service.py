"""
Payment service for payment-related business logic.

Handles payment processing, verification, and status management.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from oms.models.entities import Payment, PaymentStatus, OrderStatus
from oms.models.schemas import PaymentCreate, PaymentResponse
from oms.repositories.payment_repository import PaymentRepository
from oms.repositories.order_repository import OrderRepository


class PaymentService:
    """
    Service for managing payment operations.
    
    Handles the payment workflow:
    1. Customer pays invoice (payment created)
    2. Accountant verifies payment (payment completed)
    3. Order status updated to PAID
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize payment service.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.repository = PaymentRepository(session)
        self.order_repository = OrderRepository(session)
        self.session = session
    
    async def create_payment(self, payment_data: PaymentCreate) -> PaymentResponse:
        """
        Create a new payment for an order.
        
        Args:
            payment_data: Payment creation data
            
        Returns:
            Created payment response
            
        Raises:
            ValueError: If order not found or not in correct status
        """
        order = await self.order_repository.get(payment_data.order_id)
        if order is None:
            raise ValueError(f"Order {payment_data.order_id} not found")
        if order.status not in [OrderStatus.INVOICED, OrderStatus.ACCEPTED]:
            raise ValueError(
                f"Order {payment_data.order_id} is not in a payable status. "
                f"Current status: {order.status.value}"
            )
        
        payment = Payment(
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            currency=order.currency,
            method=payment_data.method,
            status=PaymentStatus.PENDING,
            transaction_id=payment_data.transaction_id,
        )
        created = await self.repository.create(payment)
        return PaymentResponse.model_validate(created)
    
    async def get_payment(self, payment_id: int) -> Optional[PaymentResponse]:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Payment response or None if not found
        """
        payment = await self.repository.get(payment_id)
        if payment is None:
            return None
        return PaymentResponse.model_validate(payment)
    
    async def get_payments_by_order(self, order_id: int) -> List[PaymentResponse]:
        """
        Get all payments for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            List of payment responses
        """
        payments = await self.repository.get_by_order(order_id)
        return [PaymentResponse.model_validate(p) for p in payments]
    
    async def get_payment_by_transaction(
        self, transaction_id: str
    ) -> Optional[PaymentResponse]:
        """
        Get payment by transaction ID.
        
        Args:
            transaction_id: External transaction ID
            
        Returns:
            Payment response or None if not found
        """
        payment = await self.repository.get_by_transaction_id(transaction_id)
        if payment is None:
            return None
        return PaymentResponse.model_validate(payment)
    
    async def verify_payment(self, payment_id: int) -> Optional[PaymentResponse]:
        """
        Verify and complete a payment (Accountant action).
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Updated payment response or None if not found
            
        Raises:
            ValueError: If payment is not in PENDING status
        """
        payment = await self.repository.get(payment_id)
        if payment is None:
            return None
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment {payment_id} is not in PENDING status")
        
        order = await self.order_repository.get(payment.order_id)
        if order is None:
            raise ValueError(f"Order {payment.order_id} not found")
        
        total_paid = await self.repository.get_total_paid_amount(payment.order_id)
        if total_paid + float(payment.amount) >= float(order.total_amount):
            payment.status = PaymentStatus.COMPLETED
            payment.processed_at = datetime.utcnow()
            
            order.status = OrderStatus.PAID
            await self.order_repository.update(order)
        else:
            payment.status = PaymentStatus.PROCESSING
        
        updated = await self.repository.update(payment)
        return PaymentResponse.model_validate(updated)
    
    async def fail_payment(self, payment_id: int, reason: Optional[str] = None) -> Optional[PaymentResponse]:
        """
        Mark a payment as failed.
        
        Args:
            payment_id: Payment ID
            reason: Optional failure reason
            
        Returns:
            Updated payment response or None if not found
        """
        payment = await self.repository.get(payment_id)
        if payment is None:
            return None
        
        payment.status = PaymentStatus.FAILED
        
        order = await self.order_repository.get(payment.order_id)
        if order and order.status == OrderStatus.INVOICED:
            order.status = OrderStatus.ACCEPTED
            await self.order_repository.update(order)
        
        updated = await self.repository.update(payment)
        return PaymentResponse.model_validate(updated)
    
    async def refund_payment(self, payment_id: int) -> Optional[PaymentResponse]:
        """
        Refund a completed payment.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Updated payment response or None if not found
            
        Raises:
            ValueError: If payment is not completed
        """
        payment = await self.repository.get(payment_id)
        if payment is None:
            return None
        if payment.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Payment {payment_id} is not completed")
        
        payment.status = PaymentStatus.REFUNDED
        
        order = await self.order_repository.get(payment.order_id)
        if order:
            order.status = OrderStatus.CANCELLED
            await self.order_repository.update(order)
        
        updated = await self.repository.update(payment)
        return PaymentResponse.model_validate(updated)
    
    async def get_pending_payments(self, limit: int = 100) -> List[PaymentResponse]:
        """
        Get all pending payments awaiting verification.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of pending payment responses
        """
        payments = await self.repository.get_pending_payments(limit=limit)
        return [PaymentResponse.model_validate(p) for p in payments]
    
    async def get_total_paid_amount(self, order_id: int) -> float:
        """
        Get total paid amount for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Total paid amount
        """
        return await self.repository.get_total_paid_amount(order_id)
