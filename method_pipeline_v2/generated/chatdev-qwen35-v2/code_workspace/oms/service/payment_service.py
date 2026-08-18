"""
Payment service with business logic and validation
Implements NFR 2.4 Transactions via ACID database operations
"""
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from oms.repository.payment_repository import PaymentRepository
from oms.repository.order_repository import OrderRepository
from oms.repository.invoice_repository import InvoiceRepository
from oms.domain.models import Payment, PaymentCreate, PaymentVerify, PaymentStatus, OrderStatus
from oms.infrastructure.exceptions import NotFoundException, ConflictException, ValidationException
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.database import transaction_session


class PaymentService:
    """
    Payment service implementing business logic
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = PaymentRepository(session)
        self.order_repo = OrderRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.cache = MemoryCache.get_instance()
    
    async def get_by_id(self, payment_id: str) -> Payment:
        """Get payment by ID with cache lookup"""
        # Try cache first (NFR 1.2)
        cached = await self.cache.get(f"payment:{payment_id}")
        if cached:
            return Payment(**cached)
        
        # Fallback to database
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            raise NotFoundException(f"Payment {payment_id} not found")
        
        # Populate cache
        await self.cache.set(f"payment:{payment_id}", payment.model_dump())
        return payment
    
    async def get_all(self) -> List[Payment]:
        """Get all payments"""
        return await self.repository.get_all()
    
    async def get_by_order(self, order_id: str) -> List[Payment]:
        """Get payments by order ID"""
        return await self.repository.get_by_order(order_id)
    
    async def create(self, payment: PaymentCreate) -> Payment:
        """
        Create new payment with validation
        NFR 2.4: Transaction ensures atomicity and consistency
        """
        async with transaction_session() as session:
            # Create repositories with the transaction session
            payment_repo = PaymentRepository(session)
            order_repo = OrderRepository(session)
            invoice_repo = InvoiceRepository(session)
            
            # Validate order exists and is in INVOICED state
            order = await order_repo.get_by_id(payment.orderRef)
            if not order:
                raise NotFoundException(f"Order {payment.orderRef} not found")
            
            if OrderStatus(order.status) != OrderStatus.INVOICED:
                raise ConflictException(
                    f"Order must be INVOICED to accept payment, current status: {order.status}"
                )
            
            # Validate invoice exists and amount matches
            invoice = await invoice_repo.get_by_order(payment.orderRef)
            if not invoice:
                raise ConflictException(f"No invoice found for order {payment.orderRef}")
            
            if payment.amount != invoice.totalAmount:
                raise ValidationException(
                    f"Payment amount {payment.amount} must match invoice amount {invoice.totalAmount}"
                )
            
            # Create payment
            created = await payment_repo.create(payment)
            
            # Populate cache
            await self.cache.set(f"payment:{created.id}", created.model_dump())
            
            return created
    
    async def verify_payment(self, payment_id: str, verify: PaymentVerify) -> Payment:
        """
        Verify payment (Accountant only)
        NFR 2.4: Transaction ensures state consistency
        """
        async with transaction_session() as session:
            # Create repository with the transaction session
            payment_repo = PaymentRepository(session)
            
            payment = await payment_repo.get_by_id(payment_id)
            if not payment:
                raise NotFoundException(f"Payment {payment_id} not found")
            
            # Validate status transition (PENDING -> VERIFIED or REJECTED)
            if PaymentStatus(payment.status) != PaymentStatus.PENDING:
                raise ConflictException(
                    f"Payment must be PENDING to verify, current status: {payment.status}"
                )
            
            if verify.status not in [PaymentStatus.VERIFIED, PaymentStatus.REJECTED]:
                raise ValidationException("Verification status must be VERIFIED or REJECTED")
            
            # Update payment status
            updated = await payment_repo.update_status(payment_id, verify.status)
            
            # Invalidate cache
            await self.cache.delete(f"payment:{payment_id}")
            
            return updated
    
    async def delete(self, payment_id: str) -> bool:
        """Delete payment"""
        payment = await self.repository.get_by_id(payment_id)
        if not payment:
            return False
        
        # Invalidate cache
        await self.cache.delete(f"payment:{payment_id}")
        
        return await self.repository.delete(payment_id)
