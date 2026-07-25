"""
Customer service with business logic
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from app.repositories.customer_repository import CustomerRepository
from app.models.customer import Customer, CustomerRole, BankingDetails
from app.db.tables import CustomerTable
class CustomerService:
    """Service layer for Customer operations"""
    
    def __init__(self, session: AsyncSession):
        self.repository = CustomerRepository(session)
    
    async def create_customer(
        self,
        name: str,
        address: str,
        phone: str,
        account_number: str,
        bank_name: str,
        role: str = CustomerRole.CUSTOMER,
    ) -> Customer:
        """Create a new customer"""
        entity = await self.repository.create_customer(
            name=name,
            address=address,
            phone=phone,
            banking_account_number=account_number,
            banking_bank_name=bank_name,
            role=role,
        )
        return self._to_model(entity)
    
    async def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        entity = await self.repository.get_by_id(customer_id)
        return self._to_model(entity) if entity else None
    
    async def get_all_customers(self, limit: int = 100, offset: int = 0) -> List[Customer]:
        """Get all customers"""
        entities = await self.repository.get_all(limit, offset)
        return [self._to_model(e) for e in entities]
    
    async def add_order_to_history(self, customer_id: str, order_id: str) -> bool:
        """Add order to customer's order history"""
        return await self.repository.add_to_order_history(customer_id, order_id)
    
    def _to_model(self, entity: CustomerTable) -> Customer:
        """Convert table entity to domain model"""
        try:
            return Customer(
                id=entity.id,
                name=entity.name,
                address=entity.address,
                phone=entity.phone,
                bankingDetails=BankingDetails(
                    accountNumber=entity.banking_account_number,
                    bankName=entity.banking_bank_name,
                ),
                role=entity.role,
                orderHistory=entity.order_history or [],
            )
        except ValidationError as e:
            # Re-raise as ValueError for controller to handle
            raise ValueError(str(e))
