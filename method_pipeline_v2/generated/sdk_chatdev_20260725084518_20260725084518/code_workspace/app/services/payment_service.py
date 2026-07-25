"""
Payment service with business logic
"""
from typing import List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.payment_repository import PaymentRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.order import OrderStatus
from app.db.tables import PaymentTable


class PaymentValidationError(Exception):
    """Raised when payment validation fails"""
    pass


class PaymentTransitionError(Exception):
    """Raised when invalid state transition is attempted"""
    pass


class PaymentService:
    """Service layer for Payment operations"""
    
    def __init__(self, session: AsyncSession):
        self.repository = PaymentRepository(session)
        self.order_repo = OrderRepository(session)
        self.invoice_repo = InvoiceRepository(session)
    
    async def create_payment(
        self,
        order_ref: str,
        amount: Decimal,
        method: str,
    ) -> Payment:
        """Create a new payment"""
        # Validate order exists and is in INVOICED state
        order = await self.order_repo.get_by_id(order_ref)
        if not order:
            raise PaymentValidationError(f"Order {order_ref} not found")
        
        if order.status != OrderStatus.INVOICED:
            raise PaymentValidationError(
                f"Cannot pay order in status {order.status}. Order must be INVOICED."
            )
        
        # Validate invoice exists and amount matches
        invoice = await self.invoice_repo.get_by_order_ref(order_ref)
        if not invoice:
            raise PaymentValidationError(f"No invoice found for order {order_ref}")
        
        invoice_amount = Decimal(str(invoice.total_amount))
        if amount != invoice_amount:
            raise PaymentValidationError(
                f"Payment amount {amount} must match invoice amount {invoice_amount}"
            )
        
        entity = await self.repository.create_payment(
            order_ref=order_ref,
            amount=amount,
            method=method,
            status=PaymentStatus.PENDING,
        )
        
        return self._to_model(entity)
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        entity = await self.repository.get_by_id(payment_id)
        return self._to_model(entity) if entity else None
    
    async def get_payment_by_order(self, order_ref: str) -> Optional[Payment]:
        """Get payment by order reference"""
        entity = await self.repository.get_by_order_ref(order_ref)
        return self._to_model(entity) if entity else None
    
    async def get_all_payments(self, limit: int = 100, offset: int = 0) -> List[Payment]:
        """Get all payments"""
        entities = await self.repository.get_all(limit, offset)
        return [self._to_model(e) for e in entities]
    
    async def verify_payment(self, payment_id: str) -> Payment:
        """Verify payment (PENDING -> VERIFIED)"""
        payment = await self.get_payment(payment_id)
        if not payment:
            raise PaymentValidationError(f"Payment {payment_id} not found")
        
        if payment.status != PaymentStatus.PENDING:
            raise PaymentTransitionError(
                f"Cannot verify payment in status {payment.status}"
            )
        
        entity = await self.repository.update_status(payment_id, PaymentStatus.VERIFIED)
        
        # Update order status to PAID (payment verified means order is paid)
        # Order verification (PAID -> VERIFIED) is a separate step performed by OrderStaff
        await self.order_repo.update_status(payment.orderRef, OrderStatus.PAID)
        
        # Update invoice status to PAID
        invoice = await self.invoice_repo.get_by_order_ref(payment.orderRef)
        if invoice:
            await self.invoice_repo.update_status(invoice.id, "PAID")
        return self._to_model(entity)
    
    async def reject_payment(self, payment_id: str) -> Payment:
        """Reject payment (PENDING -> REJECTED)"""
        payment = await self.get_payment(payment_id)
        if not payment:
            raise PaymentValidationError(f"Payment {payment_id} not found")
        
        if payment.status != PaymentStatus.PENDING:
            raise PaymentTransitionError(
                f"Cannot reject payment in status {payment.status}"
            )
        
        entity = await self.repository.update_status(payment_id, PaymentStatus.REJECTED)
        return self._to_model(entity)
    
    def _to_model(self, entity: PaymentTable) -> Payment:
        """Convert table entity to domain model"""
        return Payment(
            id=entity.id,
            orderRef=entity.order_ref,
            amount=Decimal(str(entity.amount)),
            timestamp=entity.timestamp,
            status=entity.status,
            method=entity.method,
        )
