"""
OMS Order Service - Business logic for order management.
"""
from typing import List, Optional
import uuid
from datetime import datetime
from decimal import Decimal
from app.domain.entities.models import Order, OrderStatus, LineItem, Address, Money, Currency
from app.domain.repositories.interfaces import OrderRepository, ProductRepository


class OrderService:
    """Service for order operations."""

    def __init__(self, order_repo: OrderRepository, product_repo: ProductRepository = None):
        self._repo = order_repo
        self._product_repo = product_repo

    def create_order(
        self,
        customer_id: str,
        line_items: List[LineItem],
        shipping_address: Optional[Address] = None,
        notes: Optional[str] = None
    ) -> Order:
        """Create a new order."""
        if self._product_repo:
            for item in line_items:
                product = self._product_repo.find_by_id(item.product_id)
                if product and product.stock_quantity >= item.quantity:
                    self._product_repo.update(
                        item.product_id,
                        {'stock_quantity': product.stock_quantity - item.quantity}
                    )
        
        subtotal = sum(item.subtotal for item in line_items)
        tax_total = subtotal * Decimal("0.1")
        discount_total = Money(amount=Decimal("0"), currency=subtotal.currency)
        total = subtotal + tax_total
        
        order = Order(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            line_items=line_items,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_total,
            total=total,
            currency=subtotal.currency,
            shipping_address=shipping_address,
            notes=notes
        )
        return self._repo.save(order)

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self._repo.find_by_id(order_id)

    def get_orders_by_customer(self, customer_id: str) -> List[Order]:
        """Get all orders for a customer."""
        return self._repo.find_by_customer(customer_id)

    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders."""
        return self._repo.find_pending_orders()

    def accept_order(self, order_id: str) -> Optional[Order]:
        """Accept an order."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return None
        
        return self._repo.update(order_id, {
            'status': OrderStatus.ACCEPTED,
            'accepted_at': datetime.utcnow()
        })

    def reject_order(self, order_id: str) -> Optional[Order]:
        """Reject an order."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return None
        
        if self._product_repo:
            for item in order.line_items:
                product = self._product_repo.find_by_id(item.product_id)
                if product:
                    self._product_repo.update(
                        item.product_id,
                        {'stock_quantity': product.stock_quantity + item.quantity}
                    )
        
        return self._repo.update(order_id, {'status': OrderStatus.REJECTED})

    def ship_order(self, order_id: str) -> Optional[Order]:
        """Ship an order."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.PAID:
            return None
        
        return self._repo.update(order_id, {
            'status': OrderStatus.SHIPPED,
            'shipped_at': datetime.utcnow()
        })

    def complete_order(self, order_id: str) -> Optional[Order]:
        """Complete an order."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.SHIPPED:
            return None
        
        return self._repo.update(order_id, {
            'status': OrderStatus.COMPLETED,
            'completed_at': datetime.utcnow()
        })

    def cancel_order(self, order_id: str) -> Optional[Order]:
        """Cancel an order."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status in [OrderStatus.SHIPPED, OrderStatus.COMPLETED]:
            return None
        
        if self._product_repo:
            for item in order.line_items:
                product = self._product_repo.find_by_id(item.product_id)
                if product:
                    self._product_repo.update(
                        item.product_id,
                        {'stock_quantity': product.stock_quantity + item.quantity}
                    )
        
        return self._repo.update(order_id, {'status': OrderStatus.CANCELLED})

    def set_invoiced(self, order_id: str, invoice_id: str) -> Optional[Order]:
        """Mark order as invoiced."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.ACCEPTED:
            return None
        
        return self._repo.update(order_id, {
            'status': OrderStatus.INVOICED,
            'invoice_id': invoice_id
        })

    def set_paid(self, order_id: str, payment_id: str) -> Optional[Order]:
        """Mark order as paid."""
        order = self._repo.find_by_id(order_id)
        if not order or order.status != OrderStatus.INVOICED:
            return None
        
        return self._repo.update(order_id, {
            'status': OrderStatus.PAID,
            'payment_id': payment_id
        })
