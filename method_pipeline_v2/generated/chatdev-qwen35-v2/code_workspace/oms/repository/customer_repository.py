"""
Customer repository with validation and business logic
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from oms.infrastructure.database import CustomerModel, BaseRepository
from oms.domain.models import Customer, CustomerCreate
from oms.infrastructure.exceptions import NotFoundException, ValidationException

class CustomerRepository:
    """
    Customer repository implementing data access with validation
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._model_class = CustomerModel
    
    async def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == customer_id)
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_domain(model)
    
    async def get_all(self) -> List[Customer]:
        """Get all customers"""
        result = await self.session.execute(select(self._model_class))
        models = list(result.scalars().all())
        return [self._to_domain(m) for m in models]
    
    async def create(self, customer: CustomerCreate) -> Customer:
        """Create new customer"""
        model = CustomerModel(
            name=customer.name,
            address=customer.address,
            phone=customer.phone,
            account_number=customer.bankingDetails.accountNumber,
            bank_name=customer.bankingDetails.bankName,
            role=customer.role.value,
            order_history='[]'
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def update(self, customer_id: str, customer: CustomerCreate) -> Optional[Customer]:
        """Update existing customer"""
        model = await self._get_model(customer_id)
        if not model:
            return None
        
        model.name = customer.name
        model.address = customer.address
        model.phone = customer.phone
        model.account_number = customer.bankingDetails.accountNumber
        model.bank_name = customer.bankingDetails.bankName
        model.role = customer.role.value
        
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def delete(self, customer_id: str) -> bool:
        """Delete customer"""
        model = await self._get_model(customer_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True
    
    async def add_to_order_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer's order history"""
        import json
        model = await self._get_model(customer_id)
        if not model:
            return False
        
        history = json.loads(model.order_history or '[]')
        if order_id not in history:
            history.append(order_id)
            model.order_history = json.dumps(history)
            await self.session.flush()
        return True
    
    async def _get_model(self, customer_id: str) -> Optional[CustomerModel]:
        """Get model by ID"""
        result = await self.session.execute(
            select(self._model_class).where(self._model_class.id == customer_id)
        )
        return result.scalar_one_or_none()
    
    def _to_domain(self, model: CustomerModel) -> Customer:
        """Convert model to domain object"""
        import json
        from oms.domain.models import CustomerRole
        return Customer(
            id=model.id,
            name=model.name,
            address=model.address,
            phone=model.phone,
            bankingDetails={
                'accountNumber': model.account_number,
                'bankName': model.bank_name
            },
            role=CustomerRole(model.role),
            orderHistory=json.loads(model.order_history or '[]')
        )
