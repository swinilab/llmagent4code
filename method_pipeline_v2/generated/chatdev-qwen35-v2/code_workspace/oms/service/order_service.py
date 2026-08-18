"""
Order service with business logic, state machine, and transaction support
Implements NFR 2.4 Transactions via ACID database operations
"""
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from oms.repository.order_repository import OrderRepository
from oms.repository.customer_repository import CustomerRepository
from oms.repository.product_repository import ProductRepository
from oms.domain.models import Order, OrderCreate, OrderUpdate, OrderStatus, LineItem
from oms.infrastructure.exceptions import NotFoundException, ConflictException, ValidationException
from oms.infrastructure.cache.memory_cache import MemoryCache
from oms.infrastructure.database import transaction_session


class OrderService:
    """
    Order service implementing business logic and state machine
    Implements NFR 2.4 via transactional semantics
    """
    
    # State machine transitions
    VALID_TRANSITIONS = {
        OrderStatus.PLACED: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
        OrderStatus.ACCEPTED: [OrderStatus.INVOICED, OrderStatus.CANCELLED],
        OrderStatus.INVOICED: [OrderStatus.PAID, OrderStatus.CANCELLED],
        OrderStatus.PAID: [OrderStatus.VERIFIED],
        OrderStatus.VERIFIED: [OrderStatus.SHIPPED],
        OrderStatus.SHIPPED: [OrderStatus.CLOSED],
        OrderStatus.CLOSED: [],
        OrderStatus.CANCELLED: []
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
        self.cache = MemoryCache.get_instance()
    
    async def get_by_id(self, order_id: str) -> Order:
        """Get order by ID with cache lookup"""
        # Try cache first (NFR 1.2)
        cached = await self.cache.get(f"order:{order_id}")
        if cached:
            return Order(**cached)
        
        # Fallback to database
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise NotFoundException(f"Order {order_id} not found")
        
    async def get_by_status(self, status: OrderStatus) -> List[Order]:
        """Get orders by status"""
        return await self.repository.get_by_status(status)
    
    async def create(self, order: OrderCreate) -> Order:
        await self.cache.set(f"order:{order_id}", order.model_dump())
        return order
    
    async def get_all(self) -> List[Order]:
        """Get all orders"""
        return await self.repository.get_all()
    
    async def get_by_customer(self, customer_id: str) -> List[Order]:
        """Get orders by customer ID"""
        return await self.repository.get_by_customer(customer_id)
    
    async def create(self, order: OrderCreate) -> Order:
        """
        Create new order with validation
        NFR 2.4: Transaction ensures atomicity of order + line items
        NFR 2.1: Exception detection for line item count validation
        """
        async with transaction_session() as session:
            # Create repositories with the transaction session
            order_repo = OrderRepository(session)
            customer_repo = CustomerRepository(session)
            product_repo = ProductRepository(session)
            
            # NFR 2.1: Validate line item count (1-100 items)
            if not order.lineItems or len(order.lineItems) < 1:
                raise ValidationException("Order must have at least 1 line item")
            
            if len(order.lineItems) > 100:
                raise ValidationException("Order cannot exceed 100 line items")
            
            # Validate customer exists
            customer = await customer_repo.get_by_id(order.customerRef)
            if not customer:
                raise NotFoundException(f"Customer {order.customerRef} not found")
            
            # Validate products and compute total
            line_items_with_price = []
            total_amount = Decimal('0.00')
            product_refs_seen = set()
            
            for item in order.lineItems:
                # Check for duplicate product refs
                if item.productRef in product_refs_seen:
                    raise ValidationException(f"Duplicate product {item.productRef} in order")
                product_refs_seen.add(item.productRef)
                
                # Validate product exists and get price
                product = await product_repo.get_by_id(item.productRef)
                if not product:
                    raise NotFoundException(f"Product {item.productRef} not found")
                
                # Create line item with price snapshot
                line_item = LineItem(
                    productRef=item.productRef,
                    quantity=item.quantity,
                    unitPriceSnapshot=product.price['amount']
                )
                line_items_with_price.append(line_item)
                
                # Accumulate total
                total_amount += line_item.quantity * line_item.unitPriceSnapshot
            
            # Ensure total is valid
            if total_amount < Decimal('0.01'):
                raise ValidationException("Order total must be at least 0.01")
            
            # Create order (transactional)
            created = await order_repo.create(order, total_amount, line_items_with_price)
            
            # Update customer order history
            await customer_repo.add_to_order_history(order.customerRef, created.id)
            
            # Populate cache
            await self.cache.set(f"order:{created.id}", created.model_dump())
            await self.cache.delete(f"customer:{order.customerRef}")
            
            return created
    
    async def update_status(self, order_id: str, update: OrderUpdate) -> Order:
        """
        Update order status with state machine validation
        NFR 2.4: Transaction ensures state consistency
        """
        async with transaction_session() as session:
            # Create repository with the transaction session
            order_repo = OrderRepository(session)
            
            order = await order_repo.get_by_id(order_id)
            if not order:
                raise NotFoundException(f"Order {order_id} not found")
            
            # Validate state transition
            current_status = OrderStatus(order.status)
            new_status = update.status
            
            if new_status not in self.VALID_TRANSITIONS.get(current_status, []):
                raise ConflictException(
                    f"Invalid status transition from {current_status.value} to {new_status.value}"
                )
            
            # Update status
            updated = await order_repo.update_status(order_id, new_status)
            
            # Invalidate cache
            await self.cache.delete(f"order:{order_id}")
            
            return updated
    
    async def set_invoice_ref(self, order_id: str, invoice_id: str) -> Order:
        """Set invoice reference for order"""
        async with transaction_session() as session:
            # Create repository with the transaction session
            order_repo = OrderRepository(session)
            
            order = await order_repo.get_by_id(order_id)
            if not order:
                raise NotFoundException(f"Order {order_id} not found")
            
            updated = await order_repo.set_invoice_ref(order_id, invoice_id)
            
            # Invalidate cache
            await self.cache.delete(f"order:{order_id}")
            
            return updated
    
    async def delete(self, order_id: str) -> bool:
        """Delete order"""
        order = await self.repository.get_by_id(order_id)
        if not order:
            return False
        
        # Invalidate cache
        await self.cache.delete(f"order:{order_id}")
        
        return await self.repository.delete(order_id)
    
    def _validate_state_transition(self, current: OrderStatus, new: OrderStatus) -> bool:
        """Validate state machine transition"""
        return new in self.VALID_TRANSITIONS.get(current, [])
