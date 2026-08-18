"""
Concrete repository implementations
"""
from typing import Optional, List, Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from oms_backend.repository.base import BaseRepository
from oms_backend.repository.models import (
    CustomerModel,
    ProductModel,
    OrderModel,
    PaymentModel,
    InvoiceModel,
)


class CustomerRepository(BaseRepository):
    """Repository for Customer operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, CustomerModel, "customer")
    
    def find_by_id(self, id: UUID) -> Optional[CustomerModel]:
        """Get customer by ID"""
        return self.get_by_id(id)
    
    def find_all(self) -> List[CustomerModel]:
        """Get all customers"""
        return self.get_all()
    
    def create_customer(self, data: Dict[str, Any]) -> CustomerModel:
        """Create a new customer"""
        return self.create(data)
    
    def update_customer(self, id: UUID, data: Dict[str, Any]) -> Optional[CustomerModel]:
        """Update customer"""
        return self.update(id, data)
    
    def delete_customer(self, id: UUID) -> bool:
        """Delete customer"""
        return self.delete(id)
    
    def add_to_order_history(self, customer_id: UUID, order_id: UUID) -> bool:
        """Add order to customer's order history"""
        customer = self.find_by_id(customer_id)
        if not customer:
            return False
        
        history = customer.order_history or []
        if order_id not in history:
            history.append(str(order_id))
            # Soft cap at 10,000 orders
            if len(history) > 10000:
                history = history[-10000:]
            customer.order_history = history
            self.session.flush()
        return True


class ProductRepository(BaseRepository):
    """Repository for Product operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, ProductModel, "product")
    
    def find_by_id(self, id: UUID) -> Optional[ProductModel]:
        """Get product by ID"""
        return self.get_by_id(id)
    
    def find_all(self) -> List[ProductModel]:
        """Get all products"""
        return self.get_all()
    
    def create_product(self, data: Dict[str, Any]) -> ProductModel:
        """Create a new product"""
        return self.create(data)
    
    def update_product(self, id: UUID, data: Dict[str, Any]) -> Optional[ProductModel]:
        """Update product"""
        return self.update(id, data)
    
    def delete_product(self, id: UUID) -> bool:
        """Delete product"""
        return self.delete(id)


class OrderRepository(BaseRepository):
    """Repository for Order operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, OrderModel, "order")
    
    def find_by_id(self, id: UUID) -> Optional[OrderModel]:
        """Get order by ID"""
        return self.get_by_id(id)
    
    def find_all(self) -> List[OrderModel]:
        """Get all orders"""
        return self.get_all()
    
    def find_by_customer(self, customer_id: UUID) -> List[OrderModel]:
        """Get orders by customer ID"""
        return self.session.query(OrderModel).filter(
            OrderModel.customer_ref == customer_id
        ).all()
    
    def create_order(self, data: Dict[str, Any]) -> OrderModel:
        """Create a new order"""
        return self.create(data)
    
    def update_order(self, id: UUID, data: Dict[str, Any]) -> Optional[OrderModel]:
        """Update order"""
        return self.update(id, data)
    
    def delete_order(self, id: UUID) -> bool:
        """Delete order"""
        return self.delete(id)
    
    def update_status(self, id: UUID, status: str) -> Optional[OrderModel]:
        """Update order status"""
        return self.update(id, {"status": status})
    
    def set_invoice_ref(self, id: UUID, invoice_id: UUID) -> Optional[OrderModel]:
        """Set invoice reference"""
        return self.update(id, {"invoice_ref": invoice_id})


class PaymentRepository(BaseRepository):
    """Repository for Payment operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, PaymentModel, "payment")
    
    def find_by_id(self, id: UUID) -> Optional[PaymentModel]:
        """Get payment by ID"""
        return self.get_by_id(id)
    
    def find_all(self) -> List[PaymentModel]:
        """Get all payments"""
        return self.get_all()
    
    def find_by_order(self, order_id: UUID) -> List[PaymentModel]:
        """Get payments by order ID"""
        return self.session.query(PaymentModel).filter(
            PaymentModel.order_ref == order_id
        ).all()
    
    def create_payment(self, data: Dict[str, Any]) -> PaymentModel:
        """Create a new payment"""
        return self.create(data)
    
    def update_payment(self, id: UUID, data: Dict[str, Any]) -> Optional[PaymentModel]:
        """Update payment"""
        return self.update(id, data)
    
    def update_status(self, id: UUID, status: str) -> Optional[PaymentModel]:
        """Update payment status"""
        return self.update(id, {"status": status})


class InvoiceRepository(BaseRepository):
    """Repository for Invoice operations"""
    
    def __init__(self, session: Session):
        super().__init__(session, InvoiceModel, "invoice")
    
    def find_by_id(self, id: UUID) -> Optional[InvoiceModel]:
        """Get invoice by ID"""
        return self.get_by_id(id)
    
    def find_all(self) -> List[InvoiceModel]:
        """Get all invoices"""
        return self.get_all()
    
    def find_by_order(self, order_id: UUID) -> Optional[InvoiceModel]:
        """Get invoice by order ID"""
        return self.session.query(InvoiceModel).filter(
            InvoiceModel.order_ref == order_id
        ).first()
    
    def create_invoice(self, data: Dict[str, Any]) -> InvoiceModel:
        """Create a new invoice"""
        return self.create(data)
    
    def update_invoice(self, id: UUID, data: Dict[str, Any]) -> Optional[InvoiceModel]:
        """Update invoice"""
        return self.update(id, data)
    
    def update_status(self, id: UUID, status: str) -> Optional[InvoiceModel]:
        """Update invoice status"""
        return self.update(id, {"status": status})
