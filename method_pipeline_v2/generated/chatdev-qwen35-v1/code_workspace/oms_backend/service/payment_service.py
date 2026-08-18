"""
Payment service layer
Business logic for payment operations
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from oms_backend.repository import PaymentRepository, OrderRepository, InvoiceRepository
from oms_backend.repository.models import PaymentModel, PaymentStatus, OrderStatus
from oms_backend.domain.models import Payment, PaymentCreate
from oms_backend.utils.exceptions import NotFoundException, ConflictException, ValidationException
from oms_backend.utils.retry import execute_with_retry


class PaymentService:
    """
    Service for payment operations.
    Handles business logic and transaction boundaries.
    NFR 2.4: Transactions - ensures ACID properties for payment processing.
    """
    
    def __init__(self, session: Session):
        """
        Initialize payment service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = PaymentRepository(session)
        self.order_repo = OrderRepository(session)
        self.invoice_repo = InvoiceRepository(session)
    
    def get_payment(self, payment_id: UUID) -> Payment:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Payment object
            
        Raises:
            NotFoundException: If payment not found
        """
        model = self.repository.find_by_id(payment_id)
        if not model:
            raise NotFoundException("Payment", str(payment_id))
        return self._to_domain(model)
    
    def get_all_payments(self) -> List[Payment]:
        """
        Get all payments.
        
        Returns:
            List of payments
        """
        models = self.repository.find_all()
        return [self._to_domain(m) for m in models]
    
    def get_payments_by_order(self, order_id: UUID) -> List[Payment]:
        """
        Get payments by order ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            List of payments
        """
        models = self.repository.find_by_order(order_id)
        return [self._to_domain(m) for m in models]
    
    def create_payment(self, data: PaymentCreate) -> Payment:
        """
        Create a new payment (Customer pays invoice).
        NFR 2.4: Transactions - validates order state and amount.
        
        Args:
            data: Payment creation data
            
        Returns:
            Created payment
            
        Raises:
            NotFoundException: If order not found
            ConflictException: If order is not in payable state
            ValidationException: If amount doesn't match invoice
        """
        # Validate order exists and is in INVOICED state
        order = self.order_repo.find_by_id(data.orderRef)
        if not order:
            raise NotFoundException("Order", str(data.orderRef))
        
        order_status = order.status.value if hasattr(order.status, 'value') else order.status
        if order_status != OrderStatus.INVOICED.value:
            raise ConflictException(
                f"Order must be in INVOICED state to pay, current state: {order_status}",
                current_state=order_status,
                expected_state="INVOICED"
            )
        
        # Validate amount matches order total
        payment_amount = Decimal(data.amount)
        order_total = order.total_amount
        if payment_amount != order_total:
            raise ValidationException(
                f"Payment amount {payment_amount} must match order total {order_total}",
                field="amount"
            )
        
        model_data = {
            "order_ref": data.orderRef,
            "amount": payment_amount,
            "timestamp": datetime.utcnow(),
            "status": PaymentStatus.PENDING,
            "method": data.method,
        }
        
        model = self.repository.create_payment(model_data)
        self.session.flush()
        
        # Update order status to PAID after payment is created
        self.order_repo.update_status(data.orderRef, OrderStatus.PAID)
        self.session.commit()
        return self._to_domain(model)
    
    def verify_payment(self, payment_id: UUID) -> Payment:
        """
        Verify payment (Accountant verifies payment).
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Updated payment
            
        Raises:
            NotFoundException: If payment not found
            ConflictException: If payment is not in PENDING state
        """
        model = self.repository.find_by_id(payment_id)
        if not model:
            raise NotFoundException("Payment", str(payment_id))
        
        current_status = model.status.value if hasattr(model.status, 'value') else model.status
        if current_status != PaymentStatus.PENDING.value:
            raise ConflictException(
                f"Payment must be in PENDING state to verify, current state: {current_status}",
                current_state=current_status,
                expected_state="PENDING"
            )
        
        model.status = PaymentStatus.VERIFIED
        self.session.flush()
        self.session.commit()
        
        # Update order status to VERIFIED (not PAID)
        self.order_repo.update_status(model.order_ref, OrderStatus.VERIFIED)
        self.session.commit()
        
        return self._to_domain(model)
    
    def reject_payment(self, payment_id: UUID) -> Payment:
        """
        Reject payment.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Updated payment
        """
        model = self.repository.find_by_id(payment_id)
        if not model:
            raise NotFoundException("Payment", str(payment_id))
        
        model.status = PaymentStatus.REJECTED
        self.session.flush()
        self.session.commit()
        return self._to_domain(model)
    
    def _to_domain(self, model: PaymentModel) -> Payment:
        """Convert database model to domain model"""
        return Payment(
            id=model.id,
            orderRef=model.order_ref,
            amount=f"{model.amount:.2f}",
            timestamp=model.timestamp,
            status=model.status.value if hasattr(model.status, 'value') else model.status,
            method=model.method.value if hasattr(model.method, 'value') else model.method,
        )
