"""
Invoice repository with validation and business logic
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from oms.infrastructure.database import InvoiceModel
from oms.domain.models import Invoice, InvoiceCreate, InvoiceStatus
from oms.infrastructure.exceptions import NotFoundException

class InvoiceRepository:
    """
    Invoice repository implementing data access with validation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._model_class = InvoiceModel
    
    async def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == invoice_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)
    
    async def get_all(self) -> List[Invoice]:
        """Get all invoices"""
        result = await self.session.execute(select(self._model_class))
        models = list(result.scalars().all())
        return [self._to_domain(m) for m in models]
    
    async def get_by_order(self, order_id: str) -> Optional[Invoice]:
        """Get invoice by order ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.order_ref == order_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)
    
    async def create(
        self,
        order_ref: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        issue_date: str,
        due_date: str
    ) -> Invoice:
        """Create new invoice"""
        model = InvoiceModel(
            order_ref=order_ref,
            billing_name=billing_name,
            billing_address=billing_address,
            total_amount=float(total_amount),
            issue_date=issue_date,
            due_date=due_date,
            status=InvoiceStatus.ISSUED.value
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def update_status(self, invoice_id: str, new_status: InvoiceStatus) -> Optional[Invoice]:
        """Update invoice status"""
        model = await self._get_model(invoice_id)
        if not model:
            return None
        
        model.status = new_status.value
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def delete(self, invoice_id: str) -> bool:
        """Delete invoice"""
        model = await self._get_model(invoice_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def _get_model(self, invoice_id: str) -> Optional[InvoiceModel]:
        """Get model by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == invoice_id)
        )
        return result.scalar_one_or_none()
    
    def _to_domain(self, model: InvoiceModel) -> Invoice:
        """Convert model to domain object"""
        from oms.domain.models import InvoiceStatus
        return Invoice(
            id=model.id,
            orderRef=model.order_ref,
            billingInfo={
                'name': model.billing_name,
                'address': model.billing_address
            },
            totalAmount=Decimal(str(model.total_amount)),
            issueDate=model.issue_date,
            dueDate=model.due_date,
            status=InvoiceStatus(model.status)
        )
