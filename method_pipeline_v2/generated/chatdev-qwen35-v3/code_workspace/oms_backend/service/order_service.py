"""
Order service with business logic and state machine
Implements NFR 2.4 (transactions) and NFR 2.2 (graceful degradation)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from decimal import Decimal
import asyncio

from oms_backend.repository.order_repository import OrderRepository
from oms_backend.repository.product_repository import ProductRepository
from oms_backend.repository.customer_repository import CustomerRepository
from oms_backend.domain.models import Order, OrderStatus, Product, Customer
from oms_backend.domain.schemas import OrderCreate
from oms_backend.config.settings import get_settings

settings = get_settings()


class OrderService:
    """Service for Order business logic with transactional guarantees"""
    
    def __init__(self, session: AsyncSession):
        self.repository = OrderRepository(session)
        self.product_repo = ProductRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.session = session
    
    async def _validate_and_compute_order(
        self, data: OrderCreate
    ) -> tuple[List[Dict[str, Any]], float]:
        """Validate line items and compute total amount"""
        line_items = []
        total = Decimal("0.00")
        
        if len(data.lineItems) < 1 or len(data.lineItems) > 100:
            raise ValueError("Order must have 1-100 line items")
        
        product_refs = set()
        for item in data.lineItems:
            # Check for duplicate products
            if item.productRef in product_refs:
                raise ValueError("Duplicate product in order")
            product_refs.add(item.productRef)
            
            # Validate quantity
            if item.quantity < 1 or item.quantity > 1000:
                raise ValueError("Quantity must be 1-1000")
            
            # Get product and validate existence
            product = await self.product_repo.get_by_id(item.productRef)
            if not product:
                raise ValueError(f"Product not found: {item.productRef}")
            
            # Snapshot the price at order time
            unit_price = Decimal(str(product.price_amount))
            line_total = unit_price * item.quantity
            total += line_total
            
            line_items.append({
                "productRef": item.productRef,
                "quantity": item.quantity,
                "unitPriceSnapshot": float(unit_price)
            })
        
        return line_items, float(total)
    
    async def create_order(self, data: OrderCreate) -> Order:
        """Create a new order with full validation (NFR 2.4 - ACID transactions)"""
        # Validate customer exists
        customer = await self.customer_repo.get_by_id(data.customerRef)
        if not customer:
            raise ValueError(f"Customer not found: {data.customerRef}")
        
        # Validate products and compute total
        line_items, total_amount = await self._validate_and_compute_order(data)
        
        # Create order in transaction
        order = await self.repository.create(data, total_amount, line_items)
        
        # Add to customer history
        await self.customer_repo.add_to_order_history(data.customerRef, order.id)
        
        return order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID with cache (NFR 1.2)"""
        from oms_backend.repository.base import db
        cache_key = f"order:{order_id}"
        cached = db.get_cached(cache_key)
        if cached:
            return cached
        
        order = await self.repository.get_by_id(order_id)
        if order:
            db.set_cached(cache_key, order)
        return order
    
    async def get_all_orders(self, limit: int = 100, offset: int = 0) -> List[Order]:
        """Get all orders"""
        return await self.repository.get_all(limit, offset)
    
    async def accept_order(self, order_id: str) -> Optional[Order]:
        """Accept order (PLACED -> ACCEPTED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.PLACED:
            raise ValueError(f"Order must be PLACED, current status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.ACCEPTED)
    
    async def invoice_order(self, order_id: str, invoice_id: str) -> Optional[Order]:
        """Set invoice reference (ACCEPTED -> INVOICED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.ACCEPTED:
            raise ValueError(f"Order must be ACCEPTED, current status: {order.status}")
        return await self.repository.set_invoice_ref(order_id, invoice_id)
    
    async def mark_order_paid(self, order_id: str) -> Optional[Order]:
        """Mark order as paid (INVOICED -> PAID)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.INVOICED:
            raise ValueError(f"Order must be INVOICED, current status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.PAID)
    
    async def verify_order(self, order_id: str) -> Optional[Order]:
        """Verify order (PAID -> VERIFIED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.PAID:
            raise ValueError(f"Order must be PAID, current status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.VERIFIED)
    
    async def ship_order(self, order_id: str) -> Optional[Order]:
        """Ship order (VERIFIED -> SHIPPED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.VERIFIED:
            raise ValueError(f"Order must be VERIFIED, current status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.SHIPPED)
    
    async def close_order(self, order_id: str) -> Optional[Order]:
        """Close order (SHIPPED -> CLOSED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Order must be SHIPPED, current status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.CLOSED)
    
    async def cancel_order(self, order_id: str) -> Optional[Order]:
        """Cancel order (any state -> CANCELLED)"""
        order = await self.get_order(order_id)
        if not order:
            return None
        if order.status in [OrderStatus.CLOSED, OrderStatus.CANCELLED]:
            raise ValueError(f"Order cannot be cancelled from status: {order.status}")
        return await self.repository.update_status(order_id, OrderStatus.CANCELLED)
