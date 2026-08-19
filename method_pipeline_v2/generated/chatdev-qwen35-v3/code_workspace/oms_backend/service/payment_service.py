"""
Payment service with business logic
Implements NFR 2.4 (transactions) and NFR 2.2 (graceful degradation via retries)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio

from oms_backend.repository.payment_repository import PaymentRepository
from oms_backend.repository.order_repository import OrderRepository
from oms_backend.repository.invoice_repository import InvoiceRepository
from oms_backend.domain.models import Payment, PaymentStatus, OrderStatus
from oms_backend.domain.schemas import PaymentCreate
from oms_backend.config.settings import get_settings

settings = get_settings()


class PaymentService:
    """Service for Payment business logic with fault tolerance"""
    
    def __init__(self, session: AsyncSession):
        self.repository = PaymentRepository(session)
        self.order_repo = OrderRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.session = session
    
    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_delay_seconds),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
        reraise=True
    )
    async def create_payment(self, data: PaymentCreate) -> Payment:
        """Create a new payment with retry logic (NFR 2.2 - Graceful Degradation)"""
        # Validate order exists and is in INVOICED state
        order = await self.order_repo.get_by_id(data.orderRef)
        if not order:
            raise ValueError(f"Order not found: {data.orderRef}")
        if order.status != OrderStatus.INVOICED:
            raise ValueError(f"Order must be INVOICED, current status: {order.status}")
        
        # Get invoice and validate amount matches
        invoice = await self.invoice_repo.get_by_order_ref(data.orderRef)
        if not invoice:
            raise ValueError(f"No invoice found for order: {data.orderRef}")
        
        # Validate payment amount matches invoice total exactly
        if float(data.amount) != float(invoice.total_amount):
            raise ValueError(
                f"Payment amount {data.amount} must match invoice total {invoice.total_amount}"
            )
        
        payment = await self.repository.create(data)
        return payment
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID with cache (NFR 1.2)"""
        from oms_backend.repository.base import db
        cache_key = f"payment:{payment_id}"
        cached = db.get_cached(cache_key)
        if cached:
            return cached
        
        payment = await self.repository.get_by_id(payment_id)
        if payment:
            db.set_cached(cache_key, payment)
        return payment
    
    async def get_all_payments(self, limit: int = 100, offset: int = 0) -> List[Payment]:
        """Get all payments"""
        return await self.repository.get_all(limit, offset)
    
    async def get_payments_by_order(self, order_ref: str) -> List[Payment]:
        """Get all payments for an order"""
        return await self.repository.get_by_order_ref(order_ref)
    
    async def verify_payment(self, payment_id: str) -> Optional[Payment]:
        """Verify payment (PENDING -> VERIFIED)"""
        payment = await self.get_payment(payment_id)
        if not payment:
            return None
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment must be PENDING, current status: {payment.status}")
        return await self.repository.update_status(payment_id, PaymentStatus.VERIFIED)
    
    async def reject_payment(self, payment_id: str) -> Optional[Payment]:
        """Reject payment (PENDING -> REJECTED)"""
        payment = await self.get_payment(payment_id)
        if not payment:
            return None
        if payment.status != PaymentStatus.PENDING:
            raise ValueError(f"Payment must be PENDING, current status: {payment.status}")
        return await self.repository.update_status(payment_id, PaymentStatus.REJECTED)
