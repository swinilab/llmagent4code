"""
Order service layer
Business logic for order operations with workflow state machine
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from oms_backend.repository import OrderRepository, CustomerRepository, ProductRepository
from oms_backend.repository.models import OrderModel, OrderStatus
from oms_backend.domain.models import Order, OrderCreate, LineItem
from oms_backend.utils.exceptions import NotFoundException, ConflictException, ValidationException
from oms_backend.utils.retry import execute_with_retry


class OrderService:
    """
    Service for order operations.
    Handles business logic, workflow state machine, and transaction boundaries.
    Implements the behavior workflow:
    1. Customer places order -> PLACED
    2. Order Staff reviews & accepts -> ACCEPTED
    3. Accountant creates invoice -> INVOICED
    4. Customer pays invoice -> PAID
    5. Accountant verifies payment -> VERIFIED
    6. Order Staff ships paid order -> SHIPPED
    7. Order Staff closes completed order -> CLOSED
    """
    
    # Valid state transitions
    STATE_TRANSITIONS = {
        "PLACED": ["ACCEPTED", "CANCELLED"],
        "ACCEPTED": ["INVOICED", "CANCELLED"],
        "INVOICED": ["PAID", "CANCELLED"],
        "PAID": ["VERIFIED"],
        "VERIFIED": ["SHIPPED"],
        "SHIPPED": ["CLOSED"],
        "CLOSED": [],
        "CANCELLED": [],
    }
    
    def __init__(self, session: Session):
        """
        Initialize order service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
    
    def get_order(self, order_id: UUID) -> Order:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order object
            
        Raises:
            NotFoundException: If order not found
        """
        model = self.repository.find_by_id(order_id)
        if not model:
            raise NotFoundException("Order", str(order_id))
        return self._to_domain(model)
    
    def get_all_orders(self) -> List[Order]:
        """
        Get all orders.
        
        Returns:
            List of orders
        """
        models = self.repository.find_all()
        return [self._to_domain(m) for m in models]
    
    def get_orders_by_customer(self, customer_id: UUID) -> List[Order]:
        """
        Get orders by customer ID.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of orders
        """
        models = self.repository.find_by_customer(customer_id)
        return [self._to_domain(m) for m in models]
    
    def create_order(self, data: OrderCreate) -> Order:
        """
        Create a new order (Customer places order).
        NFR 2.4: Transactions - atomic creation with line items.
        
        Args:
            data: Order creation data
            
        Returns:
            Created order
            
        Raises:
            NotFoundException: If customer or product not found
            ValidationException: If validation fails
        """
        # Validate customer exists
        customer = self.customer_repo.find_by_id(data.customerRef)
        if not customer:
            raise NotFoundException("Customer", str(data.customerRef))
        
        # Build line items with price snapshots
        line_items_data = []
        total_amount = Decimal("0.00")
        
        for item in data.lineItems:
            product = self.product_repo.find_by_id(item.productRef)
            if not product:
                raise NotFoundException("Product", str(item.productRef))
            
            unit_price = Decimal(str(product.price_amount))
            line_total = unit_price * item.quantity
            total_amount += line_total
            
            line_items_data.append({
                "productRef": str(item.productRef),
                "quantity": item.quantity,
                "unitPriceSnapshot": f"{unit_price:.2f}",
            })
        
        model_data = {
            "customer_ref": data.customerRef,
            "line_items": line_items_data,
            "total_amount": total_amount,
            "status": OrderStatus.PLACED,
            "invoice_ref": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        model = self.repository.create_order(model_data)
        self.session.commit()
        
        # Add to customer's order history
        self.customer_repo.add_to_order_history(data.customerRef, model.id)
        self.session.commit()
        
        return self._to_domain(model)
    
    def update_order_status(self, order_id: UUID, new_status: str) -> Order:
        """
        Update order status with state machine validation.
        
        Args:
            order_id: Order ID
            new_status: New status
            
        Returns:
            Updated order
            
        Raises:
            NotFoundException: If order not found
            ConflictException: If status transition is invalid
        """
        model = self.repository.find_by_id(order_id)
        if not model:
            raise NotFoundException("Order", str(order_id))
        
        current_status = model.status.value if hasattr(model.status, 'value') else model.status
        
        # Validate state transition
        allowed_transitions = self.STATE_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_transitions:
            raise ConflictException(
                f"Invalid status transition from {current_status} to {new_status}",
                current_state=current_status,
                expected_state=f"One of: {', '.join(allowed_transitions)}"
            )
        
        model.status = OrderStatus(new_status)
        model.updated_at = datetime.utcnow()
        self.session.flush()
        self.session.commit()
        
        # Invalidate cache
        self.repository.resynchronize(order_id)
        
        return self._to_domain(model)
    
    def accept_order(self, order_id: UUID) -> Order:
        """
        Accept order (Order Staff reviews & accepts).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order
        """
        return self.update_order_status(order_id, "ACCEPTED")
    
    def cancel_order(self, order_id: UUID) -> Order:
        """
        Cancel order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order
        """
        return self.update_order_status(order_id, "CANCELLED")
    
    def set_invoice_ref(self, order_id: UUID, invoice_id: UUID) -> Order:
        """
        Set invoice reference when invoice is created.
        
        Args:
            order_id: Order ID
            invoice_id: Invoice ID
            
        Returns:
            Updated order
        """
        model = self.repository.set_invoice_ref(order_id, invoice_id)
        if not model:
            raise NotFoundException("Order", str(order_id))
        
        # Transition to INVOICED status
        model.status = OrderStatus.INVOICED
        model.updated_at = datetime.utcnow()
        self.session.commit()
        
        return self._to_domain(model)
    
    def verify_order(self, order_id: UUID) -> Order:
        """
        Verify order (after payment verification).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order
        """
        return self.update_order_status(order_id, "VERIFIED")
    
    def ship_order(self, order_id: UUID) -> Order:
        """
        Ship order (Order Staff ships paid order).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order
        """
        return self.update_order_status(order_id, "SHIPPED")
    
    def close_order(self, order_id: UUID) -> Order:
        """
        Close order (Order Staff closes completed order).
        
        Args:
            order_id: Order ID
            
        Returns:
            Updated order
        """
        return self.update_order_status(order_id, "CLOSED")
    
    def _to_domain(self, model: OrderModel) -> Order:
        """Convert database model to domain model"""
        line_items = []
        for item in model.line_items:
            line_items.append(LineItem(
                productRef=UUID(item["productRef"]),
                quantity=item["quantity"],
                unitPriceSnapshot=item["unitPriceSnapshot"],
            ))
        
        return Order(
            id=model.id,
            customerRef=model.customer_ref,
            lineItems=line_items,
            totalAmount=f"{model.total_amount:.2f}",
            status=model.status.value if hasattr(model.status, 'value') else model.status,
            invoiceRef=model.invoice_ref,
            createdAt=model.created_at,
            updatedAt=model.updated_at,
        )
