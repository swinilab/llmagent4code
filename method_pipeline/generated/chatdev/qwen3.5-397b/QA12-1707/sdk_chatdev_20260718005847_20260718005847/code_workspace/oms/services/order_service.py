"""
Order service for business logic operations.
Handles the complete order lifecycle workflow.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import logging

from oms.models.order import Order, OrderStatus, OrderLineItem, OrderCreate, OrderReviewRequest, OrderResponse
from oms.models.customer import Customer
from oms.repositories.order_repository import OrderRepository
from oms.repositories.customer_repository import CustomerRepository

logger = logging.getLogger(__name__)


class OrderService:
    """
    Service for Order business logic.
    Handles order lifecycle, state transitions, and business rules.
    Implements graceful degradation and queue management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = OrderRepository(session)
        self.customer_repository = CustomerRepository(session)
    
    async def get_order(self, order_id: int) -> Optional[OrderResponse]:
        """Get an order by ID."""
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        return OrderResponse.model_validate(order)
    
    async def get_orders_by_customer(self, customer_id: int, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        """Get all orders for a customer."""
        orders = await self.repository.get_by_customer_id(customer_id, skip=skip, limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_orders_by_status(self, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        """Get orders by status."""
        orders = await self.repository.get_by_status(status, skip=skip, limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        """Get all orders with pagination."""
        orders = await self.repository.get_all(skip=skip, limit=limit)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def create_order(self, order_data: OrderCreate) -> OrderResponse:
        """
        Create a new order (Customer workflow step 1).
        Implements queue management by checking pending order count.
        """
        customer = await self.customer_repository.get_by_id(order_data.customer_id)
        if not customer:
            raise ValueError(f"Customer {order_data.customer_id} not found")
        
        pending_count = await self.repository.get_pending_orders_count()
        if pending_count >= 1000:
            logger.warning("Queue management: Too many pending orders")
            raise ValueError("System is at capacity. Please try again later.")
        
        order = await self.repository.create(order_data)
        return OrderResponse.model_validate(order)
    
    async def review_order(self, order_id: int, accept: bool, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """
        Review and accept/reject an order (Order Staff workflow step 2).
        """
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} is not in PENDING status")
        
        order.status = OrderStatus.REVIEWING
        order.notes = notes or order.notes
        order.reviewed_at = datetime.utcnow()
        
        if accept:
            order.status = OrderStatus.ACCEPTED
        else:
            order.status = OrderStatus.REJECTED
        
        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)
    
    async def accept_order(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """Accept an order (convenience method)."""
        return await self.review_order(order_id, accept=True, notes=notes)
    
    async def reject_order(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """Reject an order (convenience method)."""
        return await self.review_order(order_id, accept=False, notes=notes)
    
    async def update_order_status(self, order_id: int, status: OrderStatus) -> Optional[OrderResponse]:
        """Update order status directly."""
        order = await self.repository.update_status(order_id, status)
        if not order:
            return None
        return OrderResponse.model_validate(order)
    
    async def set_invoice_ref(self, order_id: int, invoice_id: int) -> Optional[OrderResponse]:
        """Set invoice reference for an order."""
        order = await self.repository.set_invoice_ref(order_id, invoice_id)
        if not order:
            return None
        return OrderResponse.model_validate(order)
    
    async def mark_order_for_shipping(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """
        Mark order for shipping (Order Staff workflow step 6).
        """
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Order {order_id} must be PAID before shipping")
        
        order.status = OrderStatus.SHIPPING
        order.notes = notes or order.notes
        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)
    
    async def mark_order_shipped(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """
        Mark order as shipped (Order Staff workflow step 6 continued).
        """
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        
        if order.status not in [OrderStatus.SHIPPING, OrderStatus.PAID]:
            raise ValueError(f"Order {order_id} is not ready for shipping")
        
        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.utcnow()
        order.notes = notes or order.notes
        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)
    
    async def complete_order(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """
        Complete/close an order (Order Staff workflow step 7).
        """
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Order {order_id} must be SHIPPED before completion")
        
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        order.notes = notes or order.notes
        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)
    
    async def cancel_order(self, order_id: int, notes: Optional[str] = None) -> Optional[OrderResponse]:
        """Cancel an order."""
        order = await self.repository.get_by_id(order_id)
        if not order:
            return None
        
        if order.status in [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.SHIPPED]:
            raise ValueError(f"Order {order_id} cannot be cancelled")
        
        order.status = OrderStatus.CANCELLED
        order.notes = notes or order.notes
        await self.session.flush()
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)
    
    async def get_pending_orders_count(self) -> int:
        """Get count of pending orders for queue management."""
        return await self.repository.get_pending_orders_count()
    
    async def get_order_count(self) -> int:
        """Get total number of orders."""
        return await self.repository.count()
