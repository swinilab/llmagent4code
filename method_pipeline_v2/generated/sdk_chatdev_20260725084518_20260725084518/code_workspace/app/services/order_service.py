"""
Order service with business logic and state machine
"""
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.order_repository import OrderRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.models.order import Order, OrderStatus, LineItem
from app.db.tables import OrderTable
from app.config.settings import Settings

settings = Settings()


class OrderValidationError(Exception):
    """Raised when order validation fails"""
    pass


class OrderTransitionError(Exception):
    """Raised when invalid state transition is attempted"""
    pass


class OrderService:
    """Service layer for Order operations with business logic"""
    
    def __init__(self, session: AsyncSession):
        self.repository = OrderRepository(session)
        self.customer_repo = CustomerRepository(session)
        self.product_repo = ProductRepository(session)
        self.invoice_repo = InvoiceRepository(session)
    
    async def create_order(
        self,
        customer_ref: str,
        line_items: List[dict],
    ) -> Order:
        """Create a new order with validation"""
        # Validate customer exists
        customer = await self.customer_repo.get_by_id(customer_ref)
        if not customer:
            raise OrderValidationError(f"Customer {customer_ref} not found")
        
        # Validate and process line items
        validated_items = []
        for item in line_items:
            product = await self.product_repo.get_by_id(item["productRef"])
            if not product:
                raise OrderValidationError(f"Product {item['productRef']} not found")
            
            quantity = item["quantity"]
            if quantity < 1 or quantity > settings.max_item_quantity:
                raise OrderValidationError(f"Quantity must be between 1 and {settings.max_item_quantity}")
            
            unit_price = Decimal(str(product.price_amount))
            validated_items.append(LineItem(
                productRef=product.id,
                quantity=quantity,
                unitPriceSnapshot=unit_price,
            ))
        
        # Check for duplicates
        product_refs = [item.productRef for item in validated_items]
        if len(product_refs) != len(set(product_refs)):
            raise OrderValidationError("Duplicate products in order not allowed")
        
        if len(validated_items) > settings.max_order_items:
            raise OrderValidationError(f"Maximum {settings.max_order_items} items per order")
        
        # Compute total
        total = Order.compute_total(validated_items)
        
        # Create order
        line_items_data = [
            {
                "productRef": str(item.productRef),
                "quantity": item.quantity,
                "unitPriceSnapshot": str(item.unitPriceSnapshot),
            }
            for item in validated_items
        ]
        
        entity = await self.repository.create_order(
            customer_ref=customer_ref,
            line_items=line_items_data,
            total_amount=total,
            status=OrderStatus.PLACED,
        )
        
        # Add to customer history
        await self.customer_repo.add_to_order_history(customer_ref, entity.id)
        
        return self._to_model(entity)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        entity = await self.repository.get_by_id(order_id)
        return self._to_model(entity) if entity else None
    
    async def get_all_orders(self, limit: int = 100, offset: int = 0) -> List[Order]:
        """Get all orders"""
        entities = await self.repository.get_all(limit, offset)
        return [self._to_model(e) for e in entities]
    
    async def get_most_recent_orders(self, limit: int = 1) -> List[Order]:
        """Get most recent orders"""
        entities = await self.repository.get_most_recent(limit)
        return [self._to_model(e) for e in entities]
    
    async def review_order(self, order_id: str) -> Order:
        """Review order (no state change, just validation)"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        return order
    
    async def accept_order(self, order_id: str) -> Order:
        """Accept order (PLACED -> ACCEPTED)"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PLACED:
            raise OrderTransitionError(f"Cannot accept order in status {order.status}")
        
        entity = await self.repository.update_status(order_id, OrderStatus.ACCEPTED)
        return self._to_model(entity)
    
    async def cancel_order(self, order_id: str) -> Order:
        """Cancel order"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        if order.status not in [OrderStatus.PLACED, OrderStatus.ACCEPTED, OrderStatus.INVOICED]:
            raise OrderTransitionError(f"Cannot cancel order in status {order.status}")
        
        entity = await self.repository.update_status(order_id, OrderStatus.CANCELLED)
        return self._to_model(entity)
    
    async def verify_order(self, order_id: str) -> Order:
        """Verify order (PAID -> VERIFIED)"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.PAID:
            raise OrderTransitionError(f"Cannot verify order in status {order.status}")
        
        entity = await self.repository.update_status(order_id, OrderStatus.VERIFIED)
        return self._to_model(entity)
    
    async def ship_order(self, order_id: str) -> Order:
        """Ship order (VERIFIED -> SHIPPED)"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.VERIFIED:
            raise OrderTransitionError(f"Cannot ship order in status {order.status}")
        
        entity = await self.repository.update_status(order_id, OrderStatus.SHIPPED)
        return self._to_model(entity)
    
    async def close_order(self, order_id: str) -> Order:
        """Close order (SHIPPED -> CLOSED)"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        if order.status != OrderStatus.SHIPPED:
            raise OrderTransitionError(f"Cannot close order in status {order.status}")
        
        entity = await self.repository.update_status(order_id, OrderStatus.CLOSED)
        return self._to_model(entity)
    
    async def set_invoice_ref(self, order_id: str, invoice_ref: str) -> Order:
        """Set invoice reference for order"""
        order = await self.get_order(order_id)
        if not order:
            raise OrderValidationError(f"Order {order_id} not found")
        
        entity = await self.repository.set_invoice_ref(order_id, invoice_ref)
        return self._to_model(entity)
    
    def _to_model(self, entity: OrderTable) -> Order:
        """Convert table entity to domain model"""
        line_items = [
            LineItem(
                productRef=item["productRef"],
                quantity=item["quantity"],
                unitPriceSnapshot=Decimal(item["unitPriceSnapshot"]),
            )
            for item in entity.line_items
        ]
        
        return Order(
            id=entity.id,
            customerRef=entity.customer_ref,
            lineItems=line_items,
            totalAmount=Decimal(str(entity.total_amount)),
            status=entity.status,
            createdAt=entity.created_at,
            updatedAt=entity.updated_at,
            invoiceRef=entity.invoice_ref,
        )
