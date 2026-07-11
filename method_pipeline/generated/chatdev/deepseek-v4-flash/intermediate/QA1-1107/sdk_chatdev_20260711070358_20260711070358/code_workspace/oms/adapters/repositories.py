"""
Repository implementations for data access.
Each repository translates between domain models and ORM models.
"""
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oms.domain.models import (
    Customer as CustomerDomain,
    Product as ProductDomain,
    Order as OrderDomain,
    OrderLineItem as OrderLineItemDomain,
    Payment as PaymentDomain,
    Invoice as InvoiceDomain,
)
from oms.domain.enums import OrderStatus, PaymentStatus, InvoiceStatus, PaymentMethod
from oms.domain.errors import EntityNotFoundError, ConcurrencyConflictError
from oms.infrastructure.orm_models import (
    CustomerModel,
    ProductModel,
    OrderModel,
    OrderLineItemModel,
    PaymentModel,
    InvoiceModel,
)


class CustomerRepository:
    """Repository for Customer entities."""

    async def get_by_id(self, session: AsyncSession, customer_id: str) -> CustomerDomain:
        result = await session.execute(
            select(CustomerModel).where(CustomerModel.id == customer_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Customer", customer_id)
        return self._to_domain(model)

    async def create(self, session: AsyncSession, customer: CustomerDomain) -> CustomerDomain:
        model = self._to_orm(customer)
        session.add(model)
        await session.flush()
        customer.id = model.id
        return customer

    async def list_all(self, session: AsyncSession) -> List[CustomerDomain]:
        result = await session.execute(select(CustomerModel))
        return [self._to_domain(row) for row in result.scalars().all()]

    def _to_domain(self, model: CustomerModel) -> CustomerDomain:
        return CustomerDomain(
            id=model.id,
            name=model.name,
            address=model.address,
            phone=model.phone,
            banking_details=model.banking_details,
            role=model.role,
            order_history=model.order_history or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_orm(self, domain: CustomerDomain) -> CustomerModel:
        return CustomerModel(
            id=domain.id,
            name=domain.name,
            address=domain.address,
            phone=domain.phone,
            banking_details=domain.banking_details,
            role=domain.role,
            order_history=domain.order_history,
        )


class ProductRepository:
    """Repository for Product entities with caching support."""

    async def get_by_id(self, session: AsyncSession, product_id: str) -> ProductDomain:
        result = await session.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Product", product_id)
        return self._to_domain(model)

    async def search(
        self, session: AsyncSession, query: str = "", limit: int = 50, offset: int = 0
    ) -> List[ProductDomain]:
        stmt = select(ProductModel)
        if query:
            stmt = stmt.where(ProductModel.description.ilike(f"%{query}%"))
        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def create(self, session: AsyncSession, product: ProductDomain) -> ProductDomain:
        model = self._to_orm(product)
        session.add(model)
        await session.flush()
        product.id = model.id
        return product

    async def update_stock(
        self, session: AsyncSession, product_id: str, available: bool
    ) -> ProductDomain:
        result = await session.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Product", product_id)
        model.stock_available = available
        await session.flush()
        return self._to_domain(model)

    def _to_domain(self, model: ProductModel) -> ProductDomain:
        return ProductDomain(
            id=model.id,
            description=model.description,
            base_price=model.base_price,
            currency=model.currency,
            stock_available=model.stock_available,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_orm(self, domain: ProductDomain) -> ProductModel:
        return ProductModel(
            id=domain.id,
            description=domain.description,
            base_price=domain.base_price,
            currency=domain.currency,
            stock_available=domain.stock_available,
        )


class OrderRepository:
    """Repository for Order entities with optimistic locking."""

    async def get_by_id(
        self, session: AsyncSession, order_id: str, for_update: bool = False
    ) -> OrderDomain:
        stmt = (
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .where(OrderModel.id == order_id)
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Order", order_id)
        return self._to_domain(model)

    async def list_by_customer(
        self, session: AsyncSession, customer_id: str
    ) -> List[OrderDomain]:
        stmt = (
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .where(OrderModel.customer_id == customer_id)
            .order_by(OrderModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def list_all(self, session: AsyncSession) -> List[OrderDomain]:
        stmt = (
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .order_by(OrderModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def create(self, session: AsyncSession, order: OrderDomain) -> OrderDomain:
        model = self._to_orm(order)
        session.add(model)
        await session.flush()
        order.id = model.id
        # Line items are cascade-saved via the relationship in _to_orm
        return order

    async def update_status(
        self,
        session: AsyncSession,
        order_id: str,
        new_status: OrderStatus,
        expected_version: int,
    ) -> OrderDomain:
        """Update order status with optimistic locking."""
        # Check current state
        result = await session.execute(
            select(OrderModel).where(OrderModel.id == order_id).with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Order", order_id)

        if model.version != expected_version:
            raise ConcurrencyConflictError("Order", order_id)

        # Update status and increment version
        model.status = new_status
        model.version += 1
        await session.flush()

        # Reload with line items
        return await self.get_by_id(session, order_id)

    async def update_invoice_ref(
        self, session: AsyncSession, order_id: str, invoice_ref: str
    ) -> OrderDomain:
        result = await session.execute(
            select(OrderModel).where(OrderModel.id == order_id).with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Order", order_id)
        model.invoice_ref = invoice_ref
        await session.flush()
        return await self.get_by_id(session, order_id)

    def _to_domain(self, model: OrderModel) -> OrderDomain:
        line_items = [
            OrderLineItemDomain(
                product_id=item.product_id,
                product_description=item.product_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
            )
            for item in model.line_items
        ]
        return OrderDomain(
            id=model.id,
            customer_id=model.customer_id,
            line_items=line_items,
            status=model.status,
            total_amount=model.total_amount,
            currency=model.currency,
            invoice_ref=model.invoice_ref,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_orm(self, domain: OrderDomain) -> OrderModel:
        """Convert domain Order to ORM OrderModel, including line items via the relationship."""
        model = OrderModel(
            id=domain.id,
            customer_id=domain.customer_id,
            status=domain.status,
            total_amount=domain.total_amount,
            currency=domain.currency,
            invoice_ref=domain.invoice_ref,
            version=domain.version,
        )
        # Populate line items so the relationship is consistent in memory
        # and cascade="all, delete-orphan" works correctly
        model.line_items = [
            OrderLineItemModel(
                product_id=item.product_id,
                product_description=item.product_description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
            )
            for item in domain.line_items
        ]
        return model


class PaymentRepository:
    """Repository for Payment entities."""

    async def get_by_id(self, session: AsyncSession, payment_id: str) -> PaymentDomain:
        result = await session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Payment", payment_id)
        return self._to_domain(model)

    async def get_by_order(self, session: AsyncSession, order_id: str) -> Optional[PaymentDomain]:
        result = await session.execute(
            select(PaymentModel).where(PaymentModel.order_id == order_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def create(self, session: AsyncSession, payment: PaymentDomain) -> PaymentDomain:
        model = self._to_orm(payment)
        session.add(model)
        await session.flush()
        payment.id = model.id
        return payment

    async def update_status(
        self, session: AsyncSession, payment_id: str, new_status: PaymentStatus
    ) -> PaymentDomain:
        result = await session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id).with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Payment", payment_id)
        model.status = new_status
        await session.flush()
        return self._to_domain(model)

    def _to_domain(self, model: PaymentModel) -> PaymentDomain:
        return PaymentDomain(
            id=model.id,
            order_id=model.order_id,
            amount=model.amount,
            currency=model.currency,
            method=model.method,
            status=model.status,
            timestamp=model.timestamp,
            updated_at=model.updated_at,
        )

    def _to_orm(self, domain: PaymentDomain) -> PaymentModel:
        return PaymentModel(
            id=domain.id,
            order_id=domain.order_id,
            amount=domain.amount,
            currency=domain.currency,
            method=domain.method,
            status=domain.status,
        )


class InvoiceRepository:
    """Repository for Invoice entities."""

    async def get_by_id(self, session: AsyncSession, invoice_id: str) -> InvoiceDomain:
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Invoice", invoice_id)
        return self._to_domain(model)

    async def get_by_order(self, session: AsyncSession, order_id: str) -> Optional[InvoiceDomain]:
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.order_id == order_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def create(self, session: AsyncSession, invoice: InvoiceDomain) -> InvoiceDomain:
        model = self._to_orm(invoice)
        session.add(model)
        await session.flush()
        invoice.id = model.id
        return invoice

    async def update_status(
        self, session: AsyncSession, invoice_id: str, new_status: InvoiceStatus
    ) -> InvoiceDomain:
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id).with_for_update()
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise EntityNotFoundError("Invoice", invoice_id)
        model.status = new_status
        await session.flush()
        return self._to_domain(model)

    def _to_domain(self, model: InvoiceModel) -> InvoiceDomain:
        return InvoiceDomain(
            id=model.id,
            order_id=model.order_id,
            billing_name=model.billing_name,
            billing_address=model.billing_address,
            total_amount=model.total_amount,
            currency=model.currency,
            status=model.status,
            issue_date=model.issue_date,
            due_date=model.due_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_orm(self, domain: InvoiceDomain) -> InvoiceModel:
        return InvoiceModel(
            id=domain.id,
            order_id=domain.order_id,
            billing_name=domain.billing_name,
            billing_address=domain.billing_address,
            total_amount=domain.total_amount,
            currency=domain.currency,
            status=domain.status,
            issue_date=domain.issue_date,
            due_date=domain.due_date,
        )
