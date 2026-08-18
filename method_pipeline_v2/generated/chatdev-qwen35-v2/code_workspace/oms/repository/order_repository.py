"""
Order repository with validation and business logic
"""
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from oms.infrastructure.database import OrderModel, LineItemModel
from oms.domain.models import Order, OrderCreate, OrderStatus, LineItem
from oms.infrastructure.exceptions import NotFoundException, ConflictException

class OrderRepository:
    """
    Order repository implementing data access with validation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._model_class = OrderModel
    
    async def get_by_id(self, order_id: str) -> Optional[Order]:
        """Get order by ID with line items"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == order_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return await self._to_domain(model)
    
    async def get_all(self) -> List[Order]:
        """Get all orders"""
        result = await self.session.execute(select(self._model_class))
        models = list(result.scalars().all())
        return [await self._to_domain(m) for m in models]
    
    async def get_by_customer(self, customer_id: str) -> List[Order]:
        """Get orders by customer ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.customer_ref == customer_id)
        )
        models = list(result.scalars().all())
        return [await self._to_domain(m) for m in models]
    
    async def get_by_status(self, status: OrderStatus) -> List[Order]:
        """Get orders by status"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.status == status.value)
        )
        models = list(result.scalars().all())
        return [await self._to_domain(m) for m in models]
    
    async def create(self, order: OrderCreate, total_amount: Decimal, line_items: List[LineItem]) -> Order:
        """Create new order with line items"""
        model = OrderModel(
            customer_ref=order.customerRef,
            total_amount=float(total_amount),
            status=OrderStatus.PLACED.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.session.flush()
        
        # Create line items
        for item in line_items:
            line_item_model = LineItemModel(
                order_id=model.id,
                product_ref=item.productRef,
                quantity=item.quantity,
                unit_price_snapshot=float(item.unitPriceSnapshot)
            )
            self.session.add(line_item_model)
        
        await self.session.flush()
        await self.session.refresh(model)
        return await self._to_domain(model)
    
    async def update_status(self, order_id: str, new_status: OrderStatus) -> Optional[Order]:
        """Update order status"""
        model = await self._get_model(order_id)
        if not model:
            return None
        
        model.status = new_status.value
        model.status = new_status.value
        model.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(model)
        return await self._to_domain(model)
    
    async def set_invoice_ref(self, order_id: str, invoice_id: str) -> Optional[Order]:
        """Set invoice reference for order"""
        model = await self._get_model(order_id)
        if not model:
            return None
        
        model.invoice_ref = invoice_id
        model.invoice_ref = invoice_id
        model.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(model)
        return await self._to_domain(model)
    
    async def delete(self, order_id: str) -> bool:
        """Delete order"""
        model = await self._get_model(order_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def _get_model(self, order_id: str) -> Optional[OrderModel]:
        """Get model by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def _to_domain(self, model: OrderModel) -> Order:
        """Convert model to domain object"""
        # Get line items
        result = await self.session.execute(
            select(LineItemModel).where(LineItemModel.order_id == model.id)
        )
        line_item_models = list(result.scalars().all())
        
        line_items = [
            LineItem(
                productRef=item.product_ref,
                quantity=item.quantity,
                unitPriceSnapshot=Decimal(str(item.unit_price_snapshot))
            )
            for item in line_item_models
        ]
        
        return Order(
            id=model.id,
            customerRef=model.customer_ref,
            lineItems=line_items,
            totalAmount=Decimal(str(model.total_amount)),
            status=model.status,
            createdAt=model.created_at.isoformat() if model.created_at else None,
            updatedAt=model.updated_at.isoformat() if model.updated_at else None,
            invoiceRef=model.invoice_ref
        )
