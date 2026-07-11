"""
Application services implementing business logic and transaction boundaries.
"""
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from oms.domain.models import (
    Customer as CustomerDomain,
    Product as ProductDomain,
    Order as OrderDomain,
    OrderLineItem as OrderLineItemDomain,
    Payment as PaymentDomain,
    Invoice as InvoiceDomain,
)
from oms.domain.enums import (
    OrderStatus,
    PaymentStatus,
    InvoiceStatus,
    PaymentMethod,
)
from oms.domain.errors import (
    EntityNotFoundError,
    BusinessRuleViolationError,
    InvalidStateTransitionError,
    ConcurrencyConflictError,
)
from oms.adapters.repositories import (
    CustomerRepository,
    ProductRepository,
    OrderRepository,
    PaymentRepository,
    InvoiceRepository,
)
from oms.infrastructure.cache import Cache
from oms.infrastructure.task_queue import TaskQueue
from oms.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CustomerService:
    """Service for customer management."""

    def __init__(self, repo: CustomerRepository):
        self._repo = repo

    async def get_customer(self, session: AsyncSession, customer_id: str) -> CustomerDomain:
        return await self._repo.get_by_id(session, customer_id)

    async def create_customer(
        self,
        session: AsyncSession,
        name: str,
        address: str,
        phone: str,
        banking_details: str,
        role: str = "CUSTOMER",
    ) -> CustomerDomain:
        customer = CustomerDomain(
            id="",  # Will be assigned by repository
            name=name,
            address=address,
            phone=phone,
            banking_details=banking_details,
            role=role,
        )
        return await self._repo.create(session, customer)

    async def list_customers(self, session: AsyncSession) -> List[CustomerDomain]:
        return await self._repo.list_all(session)


class ProductService:
    """Service for product catalog with caching."""

    def __init__(self, repo: ProductRepository, cache: Cache):
        self._repo = repo
        self._cache = cache

    @staticmethod
    def _product_to_cache_dict(product: ProductDomain) -> dict:
        """Serialize a ProductDomain to a cache-safe dict (all values JSON-serializable)."""
        return {
            "id": product.id,
            "description": product.description,
            "base_price": str(product.base_price),
            "currency": product.currency,
            "stock_available": product.stock_available,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
        }

    @staticmethod
    def _product_from_cache_dict(data: dict) -> ProductDomain:
        """Deserialize a cache dict back to a ProductDomain."""
        data["base_price"] = Decimal(data["base_price"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return ProductDomain(**data)

    async def get_product(self, session: AsyncSession, product_id: str) -> ProductDomain:
        # Try cache first
        cache_key = f"product:{product_id}"
        cached = await self._cache.get(cache_key)
        if cached:
            return self._product_from_cache_dict(cached)
        # Fall back to DB
        product = await self._repo.get_by_id(session, product_id)
        # Populate cache
        await self._cache.set(cache_key, self._product_to_cache_dict(product))
        return product

    async def search_products(
        self,
        session: AsyncSession,
        query: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[ProductDomain]:
        # For search, we use a cache key based on query params
        cache_key = f"product_search:{query}:{limit}:{offset}"
        cached = await self._cache.get(cache_key)
        if cached:
            return [self._product_from_cache_dict(p) for p in cached]
        products = await self._repo.search(session, query, limit, offset)
        # Cache search results
        await self._cache.set(
            cache_key,
            [self._product_to_cache_dict(p) for p in products],
        )
        return products

    async def create_product(
        self,
        session: AsyncSession,
        description: str,
        base_price: Decimal,
        currency: str = "USD",
        stock_available: bool = True,
    ) -> ProductDomain:
        product = ProductDomain(
            id="",
            description=description,
            base_price=base_price,
            currency=currency,
            stock_available=stock_available,
        )
        created = await self._repo.create(session, product)
        # Invalidate cache so subsequent reads get fresh data
        await self.invalidate_product_cache(created.id)
        return created

    async def invalidate_product_cache(self, product_id: str) -> None:
        """Invalidate cache when product data changes."""
        await self._cache.delete(f"product:{product_id}")
        # Also invalidate all search caches (broad invalidation)
        await self._cache.delete_pattern("product_search:*")


class OrderService:
    """Service for order management with state transition enforcement."""

    def __init__(self, repo: OrderRepository):
        self._repo = repo

    async def get_order(self, session: AsyncSession, order_id: str) -> OrderDomain:
        return await self._repo.get_by_id(session, order_id)

    async def list_orders(self, session: AsyncSession) -> List[OrderDomain]:
        return await self._repo.list_all(session)

    async def list_customer_orders(
        self, session: AsyncSession, customer_id: str
    ) -> List[OrderDomain]:
        return await self._repo.list_by_customer(session, customer_id)

    async def create_order(
        self,
        session: AsyncSession,
        customer_id: str,
        line_items_data: list[dict],
    ) -> OrderDomain:
        """Create a new order with line items."""
        # Build line items
        line_items = []
        for item in line_items_data:
            line_items.append(OrderLineItemDomain(
                product_id=item["product_id"],
                product_description=item.get("product_description", ""),
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                currency=item.get("currency", "USD"),
            ))

        order = OrderDomain(
            id="",
            customer_id=customer_id,
            line_items=line_items,
        )
        return await self._repo.create(session, order)

    async def transition_order(
        self,
        session: AsyncSession,
        order_id: str,
        target_status: OrderStatus,
        expected_version: int,
    ) -> OrderDomain:
        """
        Transition an order to a new status.
        Enforces state transitions at the domain layer.
        """
        # Load current order to validate transition
        order = await self._repo.get_by_id(session, order_id, for_update=True)
        # Domain-level validation
        order.transition_to(target_status)
        # Persist
        return await self._repo.update_status(
            session, order_id, target_status, expected_version
        )

    async def update_invoice_ref(
        self,
        session: AsyncSession,
        order_id: str,
        invoice_ref: str,
    ) -> OrderDomain:
        """Update the invoice reference on an order."""
        return await self._repo.update_invoice_ref(session, order_id, invoice_ref)


class PaymentService:
    """Service for payment processing."""

    def __init__(self, repo: PaymentRepository):
        self._repo = repo

    async def get_payment(self, session: AsyncSession, payment_id: str) -> PaymentDomain:
        return await self._repo.get_by_id(session, payment_id)

    async def get_payment_by_order(
        self, session: AsyncSession, order_id: str
    ) -> Optional[PaymentDomain]:
        return await self._repo.get_by_order(session, order_id)

    async def create_payment(
        self,
        session: AsyncSession,
        order_id: str,
        amount: Decimal,
        currency: str = "USD",
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
    ) -> PaymentDomain:
        payment = PaymentDomain(
            id="",
            order_id=order_id,
            amount=amount,
            currency=currency,
            method=method,
        )
        return await self._repo.create(session, payment)

    async def verify_payment(
        self, session: AsyncSession, payment_id: str
    ) -> PaymentDomain:
        """Mark a payment as completed."""
        return await self._repo.update_status(session, payment_id, PaymentStatus.COMPLETED)


class InvoiceService:
    """Service for invoice management."""

    def __init__(self, repo: InvoiceRepository):
        self._repo = repo

    async def get_invoice(self, session: AsyncSession, invoice_id: str) -> InvoiceDomain:
        return await self._repo.get_by_id(session, invoice_id)

    async def get_invoice_by_order(
        self, session: AsyncSession, order_id: str
    ) -> Optional[InvoiceDomain]:
        return await self._repo.get_by_order(session, order_id)

    async def create_invoice(
        self,
        session: AsyncSession,
        order_id: str,
        billing_name: str,
        billing_address: str,
        total_amount: Decimal,
        currency: str = "USD",
    ) -> InvoiceDomain:
        now = datetime.now(timezone.utc)
        invoice = InvoiceDomain(
            id="",
            order_id=order_id,
            billing_name=billing_name,
            billing_address=billing_address,
            total_amount=total_amount,
            currency=currency,
            status=InvoiceStatus.DRAFT,
            issue_date=now,
            due_date=now + timedelta(days=30),
        )
        return await self._repo.create(session, invoice)

    async def issue_invoice(
        self, session: AsyncSession, invoice_id: str
    ) -> InvoiceDomain:
        return await self._repo.update_status(session, invoice_id, InvoiceStatus.ISSUED)

    async def mark_paid(
        self, session: AsyncSession, invoice_id: str
    ) -> InvoiceDomain:
        return await self._repo.update_status(session, invoice_id, InvoiceStatus.PAID)
