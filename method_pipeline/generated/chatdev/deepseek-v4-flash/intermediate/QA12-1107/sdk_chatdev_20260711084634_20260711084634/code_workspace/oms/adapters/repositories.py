"""
Repository layer: data access with cache-aside integration.

Each repository provides CRUD operations for a domain entity, with:
  - Cache-aside reads (NFR 1.1)
  - Optimistic locking via version check (NFR 2.3)
  - Write-through cache invalidation
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from oms.adapters.orm import (
    CustomerModel,
    InvoiceModel,
    OrderModel,
    PaymentModel,
    ProductModel,
)
from oms.domain.enums import (
    InvoiceStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UserRole,
)
from oms.domain.exceptions import (
    ConcurrencyConflictError,
    CustomerNotFoundError,
    InvoiceNotFoundError,
    OrderNotFoundError,
    PaymentNotFoundError,
    ProductNotFoundError,
)
from oms.domain.models import (
    Address,
    BankingDetails,
    Customer,
    Invoice,
    LineItem,
    Money,
    Order,
    Payment,
    Product,
)
from oms.infrastructure.cache import cache_delete, cache_get, cache_set

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money_from_model(amount: Decimal, currency: str) -> Money:
    return Money(amount=amount, currency=currency)


def _line_items_from_json(items: list[dict]) -> list[LineItem]:
    return [
        LineItem(
            product_id=item["product_id"],
            product_name=item["product_name"],
            quantity=item["quantity"],
            unit_price=Money(
                amount=Decimal(str(item["unit_price_amount"])),
                currency=item.get("unit_price_currency", "USD"),
            ),
        )
        for item in (items or [])
    ]


def _line_items_to_json(items: list[LineItem]) -> list[dict]:
    return [
        {
            "product_id": item.product_id,
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price_amount": str(item.unit_price.amount),
            "unit_price_currency": item.unit_price.currency,
        }
        for item in items
    ]


# ---------------------------------------------------------------------------
# Customer Repository
# ---------------------------------------------------------------------------

class CustomerRepository:
    """Data access for Customer entities."""

    async def get_by_id(self, session: AsyncSession, customer_id: str) -> Customer:
        cached = await cache_get("customer", customer_id)
        if cached:
            return self._from_dict(cached)

        model = await session.get(CustomerModel, customer_id)
        if model is None:
            raise CustomerNotFoundError(customer_id)

        domain = self._from_orm(model)
        await cache_set("customer", customer_id, self._to_dict(domain))
        return domain

    async def save(self, session: AsyncSession, customer: Customer) -> Customer:
        model = CustomerModel(
            id=customer.id,
            name=customer.name,
            address=customer.address.__dict__ if customer.address else None,
            phone=customer.phone,
            banking_details=customer.banking_details.__dict__
            if customer.banking_details else None,
            order_history=customer.order_history,
            role=customer.role.value if hasattr(customer.role, "value") else customer.role,
            created_at=customer.created_at,
            updated_at=_utcnow(),
            version=customer.version,
        )
        session.add(model)
        await session.flush()
        await cache_delete("customer", customer.id)
        customer.version = model.version
        return customer

    async def update(self, session: AsyncSession, customer: Customer) -> Customer:
        stmt = (
            update(CustomerModel)
            .where(
                CustomerModel.id == customer.id,
                CustomerModel.version == customer.version,
            )
            .values(
                name=customer.name,
                address=customer.address.__dict__ if customer.address else None,
                phone=customer.phone,
                banking_details=customer.banking_details.__dict__
                if customer.banking_details else None,
                order_history=customer.order_history,
                role=customer.role.value if hasattr(customer.role, "value") else customer.role,
                updated_at=_utcnow(),
                version=CustomerModel.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrencyConflictError("Customer", customer.id)
        customer.version += 1
        await cache_delete("customer", customer.id)
        return customer

    def _from_orm(self, model: CustomerModel) -> Customer:
        return Customer(
            id=model.id,
            name=model.name,
            address=Address(**model.address) if model.address else None,
            phone=model.phone,
            banking_details=BankingDetails(**model.banking_details)
            if model.banking_details else None,
            order_history=model.order_history or [],
            role=UserRole(model.role),
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _from_dict(self, data: dict) -> Customer:
        return Customer(
            id=data["id"],
            name=data["name"],
            address=Address(**data["address"]) if data.get("address") else None,
            phone=data.get("phone", ""),
            banking_details=BankingDetails(**data["banking_details"])
            if data.get("banking_details") else None,
            order_history=data.get("order_history", []),
            role=UserRole(data.get("role", "CUSTOMER")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def _to_dict(self, customer: Customer) -> dict:
        return {
            "id": customer.id,
            "name": customer.name,
            "address": customer.address.__dict__ if customer.address else None,
            "phone": customer.phone,
            "banking_details": customer.banking_details.__dict__
            if customer.banking_details else None,
            "order_history": customer.order_history,
            "role": customer.role.value if hasattr(customer.role, "value") else customer.role,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "version": customer.version,
        }


# ---------------------------------------------------------------------------
# Product Repository
# ---------------------------------------------------------------------------

class ProductRepository:
    """Data access for Product entities."""

    async def get_by_id(self, session: AsyncSession, product_id: str) -> Product:
        cached = await cache_get("product", product_id)
        if cached:
            return self._from_dict(cached)

        model = await session.get(ProductModel, product_id)
        if model is None:
            raise ProductNotFoundError(product_id)

        domain = self._from_orm(model)
        await cache_set("product", product_id, self._to_dict(domain))
        return domain

    async def list_available(self, session: AsyncSession) -> list[Product]:
        result = await session.execute(
            select(ProductModel).where(ProductModel.available == True)
        )
        models = result.scalars().all()
        return [self._from_orm(m) for m in models]

    async def save(self, session: AsyncSession, product: Product) -> Product:
        model = ProductModel(
            id=product.id,
            name=product.name,
            description=product.description,
            base_price_amount=product.base_price.amount,
            base_price_currency=product.base_price.currency,
            stock=product.stock,
            available=product.available,
            created_at=product.created_at,
            updated_at=_utcnow(),
            version=product.version,
        )
        session.add(model)
        await session.flush()
        await cache_delete("product", product.id)
        product.version = model.version
        return product

    async def update(self, session: AsyncSession, product: Product) -> Product:
        stmt = (
            update(ProductModel)
            .where(
                ProductModel.id == product.id,
                ProductModel.version == product.version,
            )
            .values(
                name=product.name,
                description=product.description,
                base_price_amount=product.base_price.amount,
                base_price_currency=product.base_price.currency,
                stock=product.stock,
                available=product.available,
                updated_at=_utcnow(),
                version=ProductModel.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrencyConflictError("Product", product.id)
        product.version += 1
        await cache_delete("product", product.id)
        return product

    def _from_orm(self, model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            description=model.description,
            base_price=Money(
                amount=model.base_price_amount,
                currency=model.base_price_currency,
            ),
            stock=model.stock,
            available=model.available,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _from_dict(self, data: dict) -> Product:
        return Product(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            base_price=Money(
                amount=Decimal(str(data["base_price_amount"])),
                currency=data.get("base_price_currency", "USD"),
            ),
            stock=data.get("stock", 0),
            available=data.get("available", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def _to_dict(self, product: Product) -> dict:
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "base_price_amount": str(product.base_price.amount),
            "base_price_currency": product.base_price.currency,
            "stock": product.stock,
            "available": product.available,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
            "version": product.version,
        }


# ---------------------------------------------------------------------------
# Order Repository
# ---------------------------------------------------------------------------

class OrderRepository:
    """Data access for Order entities."""

    async def get_by_id(self, session: AsyncSession, order_id: str) -> Order:
        cached = await cache_get("order", order_id)
        if cached:
            return self._from_dict(cached)

        model = await session.get(OrderModel, order_id)
        if model is None:
            raise OrderNotFoundError(order_id)

        domain = self._from_orm(model)
        await cache_set("order", order_id, self._to_dict(domain))
        return domain

    async def get_by_customer(
        self, session: AsyncSession, customer_id: str
    ) -> list[Order]:
        result = await session.execute(
            select(OrderModel)
            .where(OrderModel.customer_id == customer_id)
            .order_by(OrderModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._from_orm(m) for m in models]

    async def get_by_status(
        self, session: AsyncSession, status: str
    ) -> list[Order]:
        result = await session.execute(
            select(OrderModel)
            .where(OrderModel.status == status)
            .order_by(OrderModel.created_at.asc())
        )
        models = result.scalars().all()
        return [self._from_orm(m) for m in models]

    async def save(self, session: AsyncSession, order: Order) -> Order:
        model = OrderModel(
            id=order.id,
            customer_id=order.customer_id,
            line_items=_line_items_to_json(order.line_items),
            status=order.status.value,
            total_amount=order.total_amount.amount,
            total_currency=order.total_amount.currency,
            invoice_ref=order.invoice_ref,
            payment_ref=order.payment_ref,
            shipping_address=order.shipping_address.__dict__
            if order.shipping_address else None,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=_utcnow(),
            version=order.version,
        )
        session.add(model)
        await session.flush()
        await cache_delete("order", order.id)
        order.version = model.version
        return order

    async def update(self, session: AsyncSession, order: Order) -> Order:
        stmt = (
            update(OrderModel)
            .where(
                OrderModel.id == order.id,
                OrderModel.version == order.version,
            )
            .values(
                customer_id=order.customer_id,
                line_items=_line_items_to_json(order.line_items),
                status=order.status.value,
                total_amount=order.total_amount.amount,
                total_currency=order.total_amount.currency,
                invoice_ref=order.invoice_ref,
                payment_ref=order.payment_ref,
                shipping_address=order.shipping_address.__dict__
                if order.shipping_address else None,
                notes=order.notes,
                updated_at=_utcnow(),
                version=OrderModel.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrencyConflictError("Order", order.id)
        order.version += 1
        await cache_delete("order", order.id)
        return order

    def _from_orm(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            customer_id=model.customer_id,
            line_items=_line_items_from_json(model.line_items),
            status=OrderStatus(model.status),
            total_amount=Money(
                amount=model.total_amount,
                currency=model.total_currency,
            ),
            invoice_ref=model.invoice_ref,
            payment_ref=model.payment_ref,
            shipping_address=Address(**model.shipping_address)
            if model.shipping_address else None,
            notes=model.notes or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _from_dict(self, data: dict) -> Order:
        return Order(
            id=data["id"],
            customer_id=data["customer_id"],
            line_items=_line_items_from_json(data.get("line_items", [])),
            status=OrderStatus(data["status"]),
            total_amount=Money(
                amount=Decimal(str(data["total_amount"])),
                currency=data.get("total_currency", "USD"),
            ),
            invoice_ref=data.get("invoice_ref"),
            payment_ref=data.get("payment_ref"),
            shipping_address=Address(**data["shipping_address"])
            if data.get("shipping_address") else None,
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def _to_dict(self, order: Order) -> dict:
        return {
            "id": order.id,
            "customer_id": order.customer_id,
            "line_items": _line_items_to_json(order.line_items),
            "status": order.status.value,
            "total_amount": str(order.total_amount.amount),
            "total_currency": order.total_amount.currency,
            "invoice_ref": order.invoice_ref,
            "payment_ref": order.payment_ref,
            "shipping_address": order.shipping_address.__dict__
            if order.shipping_address else None,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "version": order.version,
        }


# ---------------------------------------------------------------------------
# Payment Repository
# ---------------------------------------------------------------------------

class PaymentRepository:
    """Data access for Payment entities."""

    async def get_by_id(self, session: AsyncSession, payment_id: str) -> Payment:
        cached = await cache_get("payment", payment_id)
        if cached:
            return self._from_dict(cached)

        model = await session.get(PaymentModel, payment_id)
        if model is None:
            raise PaymentNotFoundError(payment_id)

        domain = self._from_orm(model)
        await cache_set("payment", payment_id, self._to_dict(domain))
        return domain

    async def get_by_order(
        self, session: AsyncSession, order_id: str
    ) -> list[Payment]:
        result = await session.execute(
            select(PaymentModel).where(PaymentModel.order_id == order_id)
        )
        models = result.scalars().all()
        return [self._from_orm(m) for m in models]

    async def save(self, session: AsyncSession, payment: Payment) -> Payment:
        model = PaymentModel(
            id=payment.id,
            order_id=payment.order_id,
            amount=payment.amount.amount,
            currency=payment.amount.currency,
            status=payment.status.value,
            method=payment.method.value,
            transaction_id=payment.transaction_id,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
            updated_at=_utcnow(),
            version=payment.version,
        )
        session.add(model)
        await session.flush()
        await cache_delete("payment", payment.id)
        payment.version = model.version
        return payment

    async def update(self, session: AsyncSession, payment: Payment) -> Payment:
        stmt = (
            update(PaymentModel)
            .where(
                PaymentModel.id == payment.id,
                PaymentModel.version == payment.version,
            )
            .values(
                status=payment.status.value,
                transaction_id=payment.transaction_id,
                paid_at=payment.paid_at,
                updated_at=_utcnow(),
                version=PaymentModel.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrencyConflictError("Payment", payment.id)
        payment.version += 1
        await cache_delete("payment", payment.id)
        return payment

    def _from_orm(self, model: PaymentModel) -> Payment:
        return Payment(
            id=model.id,
            order_id=model.order_id,
            amount=Money(amount=model.amount, currency=model.currency),
            status=PaymentStatus(model.status),
            method=PaymentMethod(model.method),
            transaction_id=model.transaction_id,
            paid_at=model.paid_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _from_dict(self, data: dict) -> Payment:
        return Payment(
            id=data["id"],
            order_id=data["order_id"],
            amount=Money(
                amount=Decimal(str(data["amount"])),
                currency=data.get("currency", "USD"),
            ),
            status=PaymentStatus(data["status"]),
            method=PaymentMethod(data.get("method", "CREDIT_CARD")),
            transaction_id=data.get("transaction_id", ""),
            paid_at=datetime.fromisoformat(data["paid_at"])
            if data.get("paid_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def _to_dict(self, payment: Payment) -> dict:
        return {
            "id": payment.id,
            "order_id": payment.order_id,
            "amount": str(payment.amount.amount),
            "currency": payment.amount.currency,
            "status": payment.status.value,
            "method": payment.method.value,
            "transaction_id": payment.transaction_id,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "created_at": payment.created_at.isoformat(),
            "updated_at": payment.updated_at.isoformat(),
            "version": payment.version,
        }


# ---------------------------------------------------------------------------
# Invoice Repository
# ---------------------------------------------------------------------------

class InvoiceRepository:
    """Data access for Invoice entities."""

    async def get_by_id(self, session: AsyncSession, invoice_id: str) -> Invoice:
        cached = await cache_get("invoice", invoice_id)
        if cached:
            return self._from_dict(cached)

        model = await session.get(InvoiceModel, invoice_id)
        if model is None:
            raise InvoiceNotFoundError(invoice_id)

        domain = self._from_orm(model)
        await cache_set("invoice", invoice_id, self._to_dict(domain))
        return domain

    async def get_by_order(
        self, session: AsyncSession, order_id: str
    ) -> list[Invoice]:
        result = await session.execute(
            select(InvoiceModel).where(InvoiceModel.order_id == order_id)
        )
        models = result.scalars().all()
        return [self._from_orm(m) for m in models]

    async def save(self, session: AsyncSession, invoice: Invoice) -> Invoice:
        model = InvoiceModel(
            id=invoice.id,
            order_id=invoice.order_id,
            customer_id=invoice.customer_id,
            billing_address=invoice.billing_address.__dict__
            if invoice.billing_address else None,
            line_items=_line_items_to_json(invoice.line_items),
            subtotal=invoice.subtotal.amount,
            tax=invoice.tax.amount,
            total=invoice.total.amount,
            currency=invoice.subtotal.currency,
            status=invoice.status.value,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            created_at=invoice.created_at,
            updated_at=_utcnow(),
            version=invoice.version,
        )
        session.add(model)
        await session.flush()
        await cache_delete("invoice", invoice.id)
        invoice.version = model.version
        return invoice

    async def update(self, session: AsyncSession, invoice: Invoice) -> Invoice:
        stmt = (
            update(InvoiceModel)
            .where(
                InvoiceModel.id == invoice.id,
                InvoiceModel.version == invoice.version,
            )
            .values(
                status=invoice.status.value,
                issue_date=invoice.issue_date,
                due_date=invoice.due_date,
                paid_at=invoice.paid_at,
                updated_at=_utcnow(),
                version=InvoiceModel.version + 1,
            )
        )
        result = await session.execute(stmt)
        if result.rowcount == 0:
            raise ConcurrencyConflictError("Invoice", invoice.id)
        invoice.version += 1
        await cache_delete("invoice", invoice.id)
        return invoice

    def _from_orm(self, model: InvoiceModel) -> Invoice:
        return Invoice(
            id=model.id,
            order_id=model.order_id,
            customer_id=model.customer_id,
            billing_address=Address(**model.billing_address)
            if model.billing_address else None,
            line_items=_line_items_from_json(model.line_items),
            subtotal=Money(amount=model.subtotal, currency=model.currency),
            tax=Money(amount=model.tax, currency=model.currency),
            total=Money(amount=model.total, currency=model.currency),
            status=InvoiceStatus(model.status),
            issue_date=model.issue_date,
            due_date=model.due_date,
            paid_at=model.paid_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _from_dict(self, data: dict) -> Invoice:
        return Invoice(
            id=data["id"],
            order_id=data["order_id"],
            customer_id=data["customer_id"],
            billing_address=Address(**data["billing_address"])
            if data.get("billing_address") else None,
            line_items=_line_items_from_json(data.get("line_items", [])),
            subtotal=Money(
                amount=Decimal(str(data["subtotal"])),
                currency=data.get("currency", "USD"),
            ),
            tax=Money(
                amount=Decimal(str(data["tax"])),
                currency=data.get("currency", "USD"),
            ),
            total=Money(
                amount=Decimal(str(data["total"])),
                currency=data.get("currency", "USD"),
            ),
            status=InvoiceStatus(data["status"]),
            issue_date=datetime.fromisoformat(data["issue_date"])
            if data.get("issue_date") else None,
            due_date=datetime.fromisoformat(data["due_date"])
            if data.get("due_date") else None,
            paid_at=datetime.fromisoformat(data["paid_at"])
            if data.get("paid_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def _to_dict(self, invoice: Invoice) -> dict:
        return {
            "id": invoice.id,
            "order_id": invoice.order_id,
            "customer_id": invoice.customer_id,
            "billing_address": invoice.billing_address.__dict__
            if invoice.billing_address else None,
            "line_items": _line_items_to_json(invoice.line_items),
            "subtotal": str(invoice.subtotal.amount),
            "tax": str(invoice.tax.amount),
            "total": str(invoice.total.amount),
            "currency": invoice.subtotal.currency,
            "status": invoice.status.value,
            "issue_date": invoice.issue_date.isoformat()
            if invoice.issue_date else None,
            "due_date": invoice.due_date.isoformat()
            if invoice.due_date else None,
            "paid_at": invoice.paid_at.isoformat()
            if invoice.paid_at else None,
            "created_at": invoice.created_at.isoformat(),
            "updated_at": invoice.updated_at.isoformat(),
            "version": invoice.version,
        }
