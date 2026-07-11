"""
Repository layer - data access abstraction over SQLAlchemy models.
Each repository provides CRUD + query methods for a single aggregate.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain import (
    Customer,
    Invoice,
    InvoiceStatus,
    LineItem,
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Product,
    UserRole,
    utcnow,
)
from app.models import (
    CustomerModel,
    InvoiceModel,
    LineItemModel,
    OrderModel,
    PaymentModel,
    ProductModel,
)


# ---------------------------------------------------------------------------
# Customer Repository
# ---------------------------------------------------------------------------
class CustomerRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, customer: Customer) -> Customer:
        model = CustomerModel(
            id=str(customer.id),
            name=customer.name,
            address=customer.address,
            phone=customer.phone,
            banking_details=customer.banking_details,
            role=customer.role,
        )
        self._session.add(model)
        self._session.flush()
        return customer

    def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        model = self._session.query(CustomerModel).filter_by(id=str(customer_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def list_all(self) -> list[Customer]:
        models = self._session.query(CustomerModel).all()
        return [self._to_domain(m) for m in models]

    @staticmethod
    def _to_domain(model: CustomerModel) -> Customer:
        return Customer(
            id=UUID(model.id),
            name=model.name,
            address=model.address,
            phone=model.phone,
            banking_details=model.banking_details,
            role=UserRole(model.role),
            order_history=[UUID(o.id) for o in model.orders],
        )


# ---------------------------------------------------------------------------
# Product Repository
# ---------------------------------------------------------------------------
class ProductRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, product: Product) -> Product:
        model = ProductModel(
            id=str(product.id),
            description=product.description,
            base_price=float(product.base_price),
            currency=product.currency,
        )
        self._session.add(model)
        self._session.flush()
        return product

    def get_by_id(self, product_id: UUID) -> Optional[Product]:
        model = self._session.query(ProductModel).filter_by(id=str(product_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def list_all(self) -> list[Product]:
        models = self._session.query(ProductModel).all()
        return [self._to_domain(m) for m in models]

    @staticmethod
    def _to_domain(model: ProductModel) -> Product:
        return Product(
            id=UUID(model.id),
            description=model.description,
            base_price=Decimal(str(model.base_price)),
            currency=model.currency,
        )


# ---------------------------------------------------------------------------
# Order Repository
# ---------------------------------------------------------------------------
class OrderRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, order: Order) -> Order:
        model = OrderModel(
            id=str(order.id),
            customer_id=str(order.customer_id),
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            invoice_id=str(order.invoice_id) if order.invoice_id else None,
            payment_id=str(order.payment_id) if order.payment_id else None,
        )
        self._session.add(model)
        self._session.flush()

        for item in order.line_items:
            li = LineItemModel(
                id=str(item.id),
                order_id=str(order.id),
                product_id=str(item.product_id),
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                currency=item.currency,
            )
            self._session.add(li)
        self._session.flush()
        return order

    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        model = self._session.query(OrderModel).filter_by(id=str(order_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def list_by_status(self, status: Optional[OrderStatus] = None) -> list[Order]:
        query = self._session.query(OrderModel)
        if status:
            query = query.filter(OrderModel.status == status)
        models = query.order_by(OrderModel.created_at.desc()).all()
        return [self._to_domain(m) for m in models]

    def update_status(self, order_id: UUID, new_status: OrderStatus) -> Optional[Order]:
        model = self._session.query(OrderModel).filter_by(id=str(order_id)).first()
        if not model:
            return None
        model.status = new_status
        model.updated_at = utcnow()
        self._session.flush()
        return self._to_domain(model)

    def update_invoice_ref(self, order_id: UUID, invoice_id: UUID) -> Optional[Order]:
        model = self._session.query(OrderModel).filter_by(id=str(order_id)).first()
        if not model:
            return None
        model.invoice_id = str(invoice_id)
        model.updated_at = utcnow()
        self._session.flush()
        return self._to_domain(model)

    def update_payment_ref(self, order_id: UUID, payment_id: UUID) -> Optional[Order]:
        model = self._session.query(OrderModel).filter_by(id=str(order_id)).first()
        if not model:
            return None
        model.payment_id = str(payment_id)
        model.updated_at = utcnow()
        self._session.flush()
        return self._to_domain(model)

    def _to_domain(self, model: OrderModel) -> Order:
        items = [
            LineItem(
                id=UUID(li.id),
                product_id=UUID(li.product_id),
                quantity=li.quantity,
                unit_price=Decimal(str(li.unit_price)),
                currency=li.currency,
            )
            for li in model.line_items
        ]
        return Order(
            id=UUID(model.id),
            customer_id=UUID(model.customer_id),
            line_items=items,
            status=OrderStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            invoice_id=UUID(model.invoice_id) if model.invoice_id else None,
            payment_id=UUID(model.payment_id) if model.payment_id else None,
        )


# ---------------------------------------------------------------------------
# Payment Repository
# ---------------------------------------------------------------------------
class PaymentRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, payment: Payment) -> Payment:
        model = PaymentModel(
            id=str(payment.id),
            order_id=str(payment.order_id),
            amount=float(payment.amount),
            currency=payment.currency,
            method=payment.method,
            status=payment.status,
            timestamp=payment.timestamp,
        )
        self._session.add(model)
        self._session.flush()
        return payment

    def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        model = self._session.query(PaymentModel).filter_by(id=str(payment_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def get_by_order_id(self, order_id: UUID) -> Optional[Payment]:
        model = self._session.query(PaymentModel).filter_by(order_id=str(order_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def update_status(self, payment_id: UUID, status: PaymentStatus) -> Optional[Payment]:
        model = self._session.query(PaymentModel).filter_by(id=str(payment_id)).first()
        if not model:
            return None
        model.status = status
        self._session.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: PaymentModel) -> Payment:
        return Payment(
            id=UUID(model.id),
            order_id=UUID(model.order_id),
            amount=Decimal(str(model.amount)),
            currency=model.currency,
            method=PaymentMethod(model.method),
            status=PaymentStatus(model.status),
            timestamp=model.timestamp,
        )


# ---------------------------------------------------------------------------
# Invoice Repository
# ---------------------------------------------------------------------------
class InvoiceRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(self, invoice: Invoice) -> Invoice:
        model = InvoiceModel(
            id=str(invoice.id),
            order_id=str(invoice.order_id),
            billing_name=invoice.billing_name,
            billing_address=invoice.billing_address,
            total_amount=float(invoice.total_amount),
            currency=invoice.currency,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            status=invoice.status,
        )
        self._session.add(model)
        self._session.flush()
        return invoice

    def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        model = self._session.query(InvoiceModel).filter_by(id=str(invoice_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def get_by_order_id(self, order_id: UUID) -> Optional[Invoice]:
        model = self._session.query(InvoiceModel).filter_by(order_id=str(order_id)).first()
        if not model:
            return None
        return self._to_domain(model)

    def update_status(self, invoice_id: UUID, status: InvoiceStatus) -> Optional[Invoice]:
        model = self._session.query(InvoiceModel).filter_by(id=str(invoice_id)).first()
        if not model:
            return None
        model.status = status
        self._session.flush()
        return self._to_domain(model)

    def update_status_by_order_id(self, order_id: UUID, status: InvoiceStatus) -> Optional[Invoice]:
        model = self._session.query(InvoiceModel).filter_by(order_id=str(order_id)).first()
        if not model:
            return None
        model.status = status
        self._session.flush()
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: InvoiceModel) -> Invoice:
        return Invoice(
            id=UUID(model.id),
            order_id=UUID(model.order_id),
            billing_name=model.billing_name,
            billing_address=model.billing_address,
            total_amount=Decimal(str(model.total_amount)),
            currency=model.currency,
            issue_date=model.issue_date,
            due_date=model.due_date,
            status=InvoiceStatus(model.status),
        )
