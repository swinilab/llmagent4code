"""
Payment repository with validation and business logic
"""
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from oms.infrastructure.database import PaymentModel
from oms.domain.models import Payment, PaymentCreate, PaymentStatus, PaymentMethod
from oms.infrastructure.exceptions import NotFoundException

class PaymentRepository:
    """
    Payment repository implementing data access with validation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._model_class = PaymentModel
    
    async def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == payment_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)
    
    async def get_all(self) -> List[Payment]:
        """Get all payments"""
        result = await self.session.execute(select(self._model_class))
        models = list(result.scalars().all())
        return [self._to_domain(m) for m in models]
    
    async def get_by_order(self, order_id: str) -> List[Payment]:
        """Get payments by order ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.order_ref == order_id)
        )
        models = list(result.scalars().all())
        return [self._to_domain(m) for m in models]
    
    async def create(self, payment: PaymentCreate) -> Payment:
        """Create new payment"""
        model = PaymentModel(
            order_ref=payment.orderRef,
            amount=float(payment.amount),
            method=payment.method.value,
            status=PaymentStatus.PENDING.value,
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def update_status(self, payment_id: str, new_status: PaymentStatus) -> Optional[Payment]:
        """Update payment status"""
        model = await self._get_model(payment_id)
        if not model:
            return None
        
        model.status = new_status.value
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def delete(self, payment_id: str) -> bool:
        """Delete payment"""
        model = await self._get_model(payment_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def _get_model(self, payment_id: str) -> Optional[PaymentModel]:
        """Get model by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == payment_id)
        )
        return result.scalar_one_or_none()
    
    def _to_domain(self, model: PaymentModel) -> Payment:
        """Convert model to domain object"""
        return Payment(
            id=model.id,
            orderRef=model.order_ref,
            amount=Decimal(str(model.amount)),
            timestamp=model.timestamp.isoformat() if model.timestamp else None,
            status=model.status,
            method=model.method
        )
