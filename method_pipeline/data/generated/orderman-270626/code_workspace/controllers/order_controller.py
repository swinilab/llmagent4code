"""
Order Controller - Handles HTTP request/response for Order operations.
Coordinates between routes and services.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderListResponse,
    OrderStatus,
)
from services.order_service import OrderService


class OrderController:
    """Controller class for Order HTTP operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the controller with a database session."""
        self.service = OrderService(db_session)

    async def get_order(self, order_id: int) -> Optional[Order]:
        """
        Get a single order by ID.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Order object if found, None otherwise
        """
        return await self.service.get_order_by_id(order_id)

    async def get_orders_by_customer(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> OrderListResponse:
        """
        Get all orders for a specific customer.
        
        Args:
            customer_id: The customer ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            OrderListResponse with orders and total count
        """
        orders = await self.service.get_orders_by_customer_id(
            customer_id=customer_id, skip=skip, limit=limit
        )
        return OrderListResponse(orders=orders, total=len(orders))

    async def get_orders_by_status(
        self, status: OrderStatus, skip: int = 0, limit: int = 100
    ) -> OrderListResponse:
        """
        Get all orders with a specific status.
        
        Args:
            status: Order status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            OrderListResponse with orders and total count
        """
        orders = await self.service.get_orders_by_status(
            status=status, skip=skip, limit=limit
        )
        return OrderListResponse(orders=orders, total=len(orders))

    async def get_all_orders(
        self, skip: int = 0, limit: int = 100
    ) -> OrderListResponse:
        """
        Get all orders with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            OrderListResponse with orders and total count
        """
        orders = await self.service.get_all_orders(skip=skip, limit=limit)
        total = await self.service.get_order_count()
        return OrderListResponse(orders=orders, total=total)

    async def create_order(self, order_data: OrderCreate) -> Order:
        """
        Create a new order (Customer action).
        
        Args:
            order_data: OrderCreate object with order information
            
        Returns:
            Created Order object
        """
        return await self.service.create_order(order_data)

    async def accept_order(self, order_id: int) -> Optional[Order]:
        """
        Accept an order (Order Staff action).
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.accept_order(order_id)

    async def update_order(
        self, order_id: int, order_data: OrderUpdate
    ) -> Optional[Order]:
        """
        Update an existing order.
        
        Args:
            order_id: The unique order ID
            order_data: OrderUpdate object with updated information
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.update_order(order_id, order_data)

    async def set_order_invoice(self, order_id: int, invoice_id: int) -> Optional[Order]:
        """
        Set the invoice ID for an order.
        
        Args:
            order_id: The unique order ID
            invoice_id: The invoice ID to associate
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.set_order_invoice(order_id, invoice_id)

    async def mark_order_paid(self, order_id: int) -> Optional[Order]:
        """
        Mark an order as paid.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.mark_order_paid(order_id)

    async def ship_order(self, order_id: int) -> Optional[Order]:
        """
        Ship an order (Order Staff action after payment).
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.ship_order(order_id)

    async def complete_order(self, order_id: int) -> Optional[Order]:
        """
        Complete/close an order (Order Staff action after shipping).
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.complete_order(order_id)

    async def cancel_order(self, order_id: int) -> Optional[Order]:
        """
        Cancel an order.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            Updated Order object if found, None otherwise
        """
        return await self.service.cancel_order(order_id)

    async def delete_order(self, order_id: int) -> bool:
        """
        Delete an order.
        
        Args:
            order_id: The unique order ID
            
        Returns:
            True if deleted successfully, False if not found
        """
        return await self.service.delete_order(order_id)
