"""
Customer service layer
Business logic for customer operations
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from oms_backend.repository import CustomerRepository
from oms_backend.repository.models import CustomerModel
from oms_backend.domain.models import Customer, CustomerCreate
from oms_backend.utils.exceptions import NotFoundException, ValidationException


class CustomerService:
    """
    Service for customer operations.
    Handles business logic and transaction boundaries.
    """
    
    def __init__(self, session: Session):
        """
        Initialize customer service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = CustomerRepository(session)
    
    def get_customer(self, customer_id: UUID) -> Customer:
        """
        Get customer by ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer object
            
        Raises:
            NotFoundException: If customer not found
        """
        model = self.repository.find_by_id(customer_id)
        if not model:
            raise NotFoundException("Customer", str(customer_id))
        return self._to_domain(model)
    
    def get_all_customers(self) -> List[Customer]:
        """
        Get all customers.
        
        Returns:
            List of customers
        """
        models = self.repository.find_all()
        return [self._to_domain(m) for m in models]
    
    def create_customer(self, data: CustomerCreate) -> Customer:
        """
        Create a new customer.
        
        Args:
            data: Customer creation data
            
        Returns:
            Created customer
        """
        model_data = {
            "name": data.name,
            "address": data.address,
            "phone": data.phone,
            "account_number": data.bankingDetails.accountNumber,
            "bank_name": data.bankingDetails.bankName,
            "role": data.role,
            "order_history": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        model = self.repository.create_customer(model_data)
        self.session.commit()
        return self._to_domain(model)
    
    def update_customer(self, customer_id: UUID, data: Dict[str, Any]) -> Customer:
        """
        Update customer.
        
        Args:
            customer_id: Customer ID
            data: Update data
            
        Returns:
            Updated customer
            
        Raises:
            NotFoundException: If customer not found
        """
        model = self.repository.update_customer(customer_id, {
            **data,
            "updated_at": datetime.utcnow()
        })
        if not model:
            raise NotFoundException("Customer", str(customer_id))
        self.session.commit()
        return self._to_domain(model)
    
    def delete_customer(self, customer_id: UUID) -> bool:
        """
        Delete customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundException: If customer not found
        """
        if not self.repository.delete_customer(customer_id):
            raise NotFoundException("Customer", str(customer_id))
        self.session.commit()
        return True
    
    def add_order_to_history(self, customer_id: UUID, order_id: UUID) -> bool:
        """
        Add order to customer's order history.
        
        Args:
            customer_id: Customer ID
            order_id: Order ID
            
        Returns:
            True if added successfully
        """
        result = self.repository.add_to_order_history(customer_id, order_id)
        if result:
            self.session.commit()
        return result
    
    def _to_domain(self, model: CustomerModel) -> Customer:
        """Convert database model to domain model"""
        return Customer(
            id=model.id,
            name=model.name,
            address=model.address,
            phone=model.phone,
            bankingDetails={
                "accountNumber": model.account_number,
                "bankName": model.bank_name,
            },
            role=model.role.value if hasattr(model.role, 'value') else model.role,
            orderHistory=[UUID(oid) for oid in (model.order_history or [])],
            createdAt=model.created_at,
            updatedAt=model.updated_at,
        )
