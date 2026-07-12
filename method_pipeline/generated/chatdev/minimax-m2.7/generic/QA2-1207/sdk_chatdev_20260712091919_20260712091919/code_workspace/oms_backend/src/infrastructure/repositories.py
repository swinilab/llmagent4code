"""
Repository pattern implementation for data access.
Each repository handles one aggregate root and provides CRUD + query operations.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4
from sqlalchemy.orm import Session, relationship
from sqlalchemy.exc import IntegrityError

from . import models as db_models
from ..domain.models import (
    Customer, Order, Product, Payment, Invoice, LineItem,
    Address, BankingDetails, OrderStatus, PaymentStatus, InvoiceStatus,
    OrderSnapshot
)

logger = logging.getLogger(__name__)


def utcnow():
    """Get current UTC time."""
    return datetime.now(timezone.utc)


class BaseRepository:
    """Base repository with common operations."""

    def __init__(self, db: Session, model_class):
        self.db = db
        self.model_class = model_class

    def _to_domain(self, db_obj) -> Any:
        raise NotImplementedError

    def _to_db(self, domain_obj) -> Any:
        raise NotImplementedError

    def get_by_id(self, id: str) -> Optional[Any]:
        db_obj = self.db.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
        return self._to_domain(db_obj) if db_obj else None

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Any]:
        db_objs = self.db.query(self.model_class).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]

    def create(self, domain_obj) -> Any:
        db_obj = self._to_db(domain_obj)
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return self._to_domain(db_obj)

    def update(self, domain_obj) -> Any:
        db_obj = self.db.query(self.model_class).filter(
            self.model_class.id == domain_obj.id
        ).first()
        if db_obj:
            for key, value in self._get_update_dict(domain_obj).items():
                setattr(db_obj, key, value)
            db_obj.updated_at = utcnow()
            self.db.flush()
            self.db.refresh(db_obj)
            return self._to_domain(db_obj)
        return None

    def delete(self, id: str) -> bool:
        db_obj = self.db.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
        if db_obj:
            self.db.delete(db_obj)
            self.db.flush()
            return True
        return False

    def _get_update_dict(self, domain_obj) -> Dict[str, Any]:
        raise NotImplementedError


class CustomerRepository(BaseRepository):
    """Repository for Customer aggregate."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.CustomerModel)

    def _to_domain(self, db_obj: db_models.CustomerModel) -> Customer:
        address = None
        if db_obj.address_json:
            address = Address.from_dict(db_obj.address_json)
        banking = None
        if db_obj.banking_details_json:
            banking = BankingDetails.from_dict(db_obj.banking_details_json)

        role = db_obj.role
        if hasattr(role, 'value'):
            role = role.value

        return Customer(
            id=db_obj.id,
            name=db_obj.name,
            email=db_obj.email,
            phone=db_obj.phone,
            address=address,
            banking_details=banking,
            role=role,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at
        )

    def _to_db(self, customer: Customer) -> db_models.CustomerModel:
        return db_models.CustomerModel(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            address_json=customer.address.to_dict() if customer.address else None,
            banking_details_json=customer.banking_details.to_dict() if customer.banking_details else None,
            role=customer.role if hasattr(customer.role, 'value') else customer.role,
            created_at=customer.created_at,
            updated_at=customer.updated_at
        )

    def _get_update_dict(self, customer: Customer) -> Dict[str, Any]:
        return {
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "address_json": customer.address.to_dict() if customer.address else None,
            "banking_details_json": customer.banking_details.to_dict() if customer.banking_details else None,
            "role": customer.role if hasattr(customer.role, 'value') else customer.role,
        }

    def get_by_email(self, email: str) -> Optional[Customer]:
        db_obj = self.db.query(db_models.CustomerModel).filter(
            db_models.CustomerModel.email == email
        ).first()
        return self._to_domain(db_obj) if db_obj else None


class ProductRepository(BaseRepository):
    """Repository for Product aggregate."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.ProductModel)

    def _to_domain(self, db_obj: db_models.ProductModel) -> Product:
        return Product(
            id=db_obj.id,
            sku=db_obj.sku,
            description=db_obj.description,
            base_price=db_obj.base_price,
            currency=db_obj.currency,
            stock_quantity=db_obj.stock_quantity,
            is_active=db_obj.is_active,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at
        )

    def _to_db(self, product: Product) -> db_models.ProductModel:
        return db_models.ProductModel(
            id=product.id,
            sku=product.sku,
            description=product.description,
            base_price=product.base_price,
            currency=product.currency,
            stock_quantity=product.stock_quantity,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at
        )

    def _get_update_dict(self, product: Product) -> Dict[str, Any]:
        return {
            "sku": product.sku,
            "description": product.description,
            "base_price": product.base_price,
            "currency": product.currency,
            "stock_quantity": product.stock_quantity,
            "is_active": product.is_active,
        }

    def get_by_sku(self, sku: str) -> Optional[Product]:
        db_obj = self.db.query(db_models.ProductModel).filter(
            db_models.ProductModel.sku == sku
        ).first()
        return self._to_domain(db_obj) if db_obj else None

    def get_active_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        db_objs = self.db.query(db_models.ProductModel).filter(
            db_models.ProductModel.is_active == True
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]


class OrderRepository(BaseRepository):
    """Repository for Order aggregate with idempotency support."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.OrderModel)

    def _to_domain(self, db_obj: db_models.OrderModel) -> Order:
        line_items = []
        for li_db in db_obj.line_items:
            line_items.append(LineItem(
                id=li_db.id,
                product_id=li_db.product_id,
                product_description=li_db.product_description,
                quantity=li_db.quantity,
                unit_price=li_db.unit_price,
                currency=li_db.currency
            ))

        shipping_address = None
        if db_obj.shipping_address_json:
            shipping_address = Address.from_dict(db_obj.shipping_address_json)

        status = db_obj.status
        if hasattr(status, 'value'):
            status = status.value

        return Order(
            id=db_obj.id,
            customer_id=db_obj.customer_id,
            line_items=line_items,
            status=status,
            subtotal=db_obj.subtotal,
            tax=db_obj.tax,
            shipping=db_obj.shipping,
            total=db_obj.total,
            currency=db_obj.currency,
            invoice_id=db_obj.invoice_id,
            shipping_address=shipping_address,
            notes=db_obj.notes,
            idempotency_key=db_obj.idempotency_key,
            tracking_number=db_obj.tracking_number,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at,
            accepted_at=db_obj.accepted_at,
            shipped_at=db_obj.shipped_at,
            completed_at=db_obj.completed_at
        )

    def _to_db(self, order: Order) -> db_models.OrderModel:
        db_order = db_models.OrderModel(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status.value if hasattr(order.status, 'value') else order.status,
            subtotal=order.subtotal,
            tax=order.tax,
            shipping=order.shipping,
            total=order.total,
            currency=order.currency,
            invoice_id=order.invoice_id,
            shipping_address_json=order.shipping_address.to_dict() if order.shipping_address else None,
            notes=order.notes,
            idempotency_key=order.idempotency_key,
            tracking_number=order.tracking_number,
            created_at=order.created_at or utcnow(),
            updated_at=order.updated_at or utcnow(),
            accepted_at=order.accepted_at,
            shipped_at=order.shipped_at,
            completed_at=order.completed_at
        )

        for li in order.line_items:
            li_db = db_models.LineItemModel(
                id=li.id or str(uuid4()),
                order_id=order.id,
                product_id=li.product_id,
                product_description=li.product_description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                currency=li.currency
            )
            db_order.line_items.append(li_db)

        return db_order

    def _get_update_dict(self, order: Order) -> Dict[str, Any]:
        return {
            "customer_id": order.customer_id,
            "status": order.status.value if hasattr(order.status, 'value') else order.status,
            "subtotal": order.subtotal,
            "tax": order.tax,
            "shipping": order.shipping,
            "total": order.total,
            "currency": order.currency,
            "invoice_id": order.invoice_id,
            "shipping_address_json": order.shipping_address.to_dict() if order.shipping_address else None,
            "notes": order.notes,
            "idempotency_key": order.idempotency_key,
            "tracking_number": order.tracking_number,
            "accepted_at": order.accepted_at,
            "shipped_at": order.shipped_at,
            "completed_at": order.completed_at
        }

    def get_by_idempotency_key(self, key: str) -> Optional[Order]:
        db_obj = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.idempotency_key == key
        ).first()
        return self._to_domain(db_obj) if db_obj else None

    def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 100) -> List[Order]:
        db_objs = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.customer_id == customer_id
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Order]:
        db_objs = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.status == status
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]

    def get_pending_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        db_objs = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.status.in_(["pending", "accepted", "invoiced", "paid"])
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]
        db_objs = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.status.in_(["pending", "accepted", "invoiced", "paid"])
        ).all()
        return [self._to_domain(obj) for obj in db_objs]

    def create_with_idempotency(self, order: Order) -> tuple:
        """Create order with idempotency check."""
        existing = self.get_by_idempotency_key(order.idempotency_key)
        if existing:
            return existing, False

        db_order = self._to_db(order)
        self.db.add(db_order)
        self.db.flush()
        self.db.refresh(db_order)
        return self._to_domain(db_order), True

    def update_with_refresh(self, order: Order) -> Order:
        """Update order and refresh from database."""
        db_obj = self.db.query(db_models.OrderModel).filter(
            db_models.OrderModel.id == order.id
        ).first()
        if db_obj:
            for key, value in self._get_update_dict(order).items():
                setattr(db_obj, key, value)
            db_obj.updated_at = utcnow()
            self.db.flush()

            for li in order.line_items:
                li_db = self.db.query(db_models.LineItemModel).filter(
                    db_models.LineItemModel.id == li.id
                ).first()
                if li_db:
                    li_db.product_id = li.product_id
                    li_db.product_description = li.product_description
                    li_db.quantity = li.quantity
                    li_db.unit_price = li.unit_price
                    li_db.currency = li.currency

            self.db.flush()
            self.db.refresh(db_obj)
            return self._to_domain(db_obj)
        return None


class InvoiceRepository(BaseRepository):
    """Repository for Invoice aggregate."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.InvoiceModel)

    def _to_domain(self, db_obj: db_models.InvoiceModel) -> Invoice:
        billing_address = None
        if db_obj.billing_address_json:
            billing_address = Address.from_dict(db_obj.billing_address_json)

        status = db_obj.status
        if hasattr(status, 'value'):
            status = status.value

        return Invoice(
            id=db_obj.id,
            order_id=db_obj.order_id,
            customer_id=db_obj.customer_id,
            billing_address=billing_address,
            subtotal=db_obj.subtotal,
            tax=db_obj.tax,
            total=db_obj.total,
            currency=db_obj.currency,
            status=status,
            issue_date=db_obj.issue_date,
            due_date=db_obj.due_date,
            paid_date=db_obj.paid_date,
            idempotency_key=db_obj.idempotency_key,
            created_at=db_obj.created_at,
            updated_at=db_obj.updated_at
        )

    def _to_db(self, invoice: Invoice) -> db_models.InvoiceModel:
        return db_models.InvoiceModel(
            id=invoice.id,
            order_id=invoice.order_id,
            customer_id=invoice.customer_id,
            billing_address_json=invoice.billing_address.to_dict() if invoice.billing_address else None,
            subtotal=invoice.subtotal,
            tax=invoice.tax,
            total=invoice.total,
            currency=invoice.currency,
            status=invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
            issue_date=invoice.issue_date,
            due_date=invoice.due_date,
            paid_date=invoice.paid_date,
            idempotency_key=invoice.idempotency_key,
            created_at=invoice.created_at or utcnow(),
            updated_at=invoice.updated_at or utcnow()
        )

    def _get_update_dict(self, invoice: Invoice) -> Dict[str, Any]:
        return {
            "order_id": invoice.order_id,
            "customer_id": invoice.customer_id,
            "billing_address_json": invoice.billing_address.to_dict() if invoice.billing_address else None,
            "subtotal": invoice.subtotal,
            "tax": invoice.tax,
            "total": invoice.total,
            "currency": invoice.currency,
            "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
            "issue_date": invoice.issue_date,
            "due_date": invoice.due_date,
            "paid_date": invoice.paid_date,
            "idempotency_key": invoice.idempotency_key,
        }

    def get_by_order(self, order_id: str) -> Optional[Invoice]:
        db_obj = self.db.query(db_models.InvoiceModel).filter(
            db_models.InvoiceModel.order_id == order_id
        ).first()
        return self._to_domain(db_obj) if db_obj else None

    def get_by_customer(self, customer_id: str, skip: int = 0, limit: int = 100) -> List[Invoice]:
        db_objs = self.db.query(db_models.InvoiceModel).filter(
            db_models.InvoiceModel.customer_id == customer_id
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Invoice]:
        db_objs = self.db.query(db_models.InvoiceModel).filter(
            db_models.InvoiceModel.status == status
        ).offset(skip).limit(limit).all()
        return [self._to_domain(obj) for obj in db_objs]

    def create_with_idempotency(self, invoice: Invoice) -> tuple:
        """Create invoice with idempotency check."""
        if invoice.idempotency_key:
            db_obj = self.db.query(db_models.InvoiceModel).filter(
                db_models.InvoiceModel.idempotency_key == invoice.idempotency_key
            ).first()
            if db_obj:
                return self._to_domain(db_obj), False

        db_invoice = self._to_db(invoice)
        self.db.add(db_invoice)
        self.db.flush()
        self.db.refresh(db_invoice)
        return self._to_domain(db_invoice), True


class PaymentRepository(BaseRepository):
    """Repository for Payment aggregate."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.PaymentModel)

    def _to_domain(self, db_obj: db_models.PaymentModel) -> Payment:
        status = db_obj.status
        if hasattr(status, 'value'):
            status = status.value

        return Payment(
            id=db_obj.id,
            order_id=db_obj.order_id,
            invoice_id=db_obj.invoice_id,
            customer_id=db_obj.customer_id,
            amount=db_obj.amount,
            currency=db_obj.currency,
            method=db_obj.method,
            status=status,
            transaction_ref=db_obj.transaction_ref,
            idempotency_key=db_obj.idempotency_key,
            created_at=db_obj.created_at,
            processed_at=db_obj.processed_at
        )

    def _to_db(self, payment: Payment) -> db_models.PaymentModel:
        return db_models.PaymentModel(
            id=payment.id,
            order_id=payment.order_id,
            invoice_id=payment.invoice_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            method=payment.method,
            status=payment.status.value if hasattr(payment.status, 'value') else payment.status,
            transaction_ref=payment.transaction_ref,
            idempotency_key=payment.idempotency_key,
            created_at=payment.created_at or utcnow(),
            processed_at=payment.processed_at
        )

    def _get_update_dict(self, payment: Payment) -> Dict[str, Any]:
        return {
            "order_id": payment.order_id,
            "invoice_id": payment.invoice_id,
            "customer_id": payment.customer_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "method": payment.method,
            "status": payment.status.value if hasattr(payment.status, 'value') else payment.status,
            "transaction_ref": payment.transaction_ref,
            "idempotency_key": payment.idempotency_key,
            "processed_at": payment.processed_at,
        }

    def get_by_order(self, order_id: str) -> List[Payment]:
        db_objs = self.db.query(db_models.PaymentModel).filter(
            db_models.PaymentModel.order_id == order_id
        ).all()
        return [self._to_domain(obj) for obj in db_objs]

    def get_by_invoice(self, invoice_id: str) -> List[Payment]:
        db_objs = self.db.query(db_models.PaymentModel).filter(
            db_models.PaymentModel.invoice_id == invoice_id
        ).all()
        return [self._to_domain(obj) for obj in db_objs]

    def get_by_idempotency_key(self, key: str) -> Optional[Payment]:
        db_obj = self.db.query(db_models.PaymentModel).filter(
            db_models.PaymentModel.idempotency_key == key
        ).first()
        return self._to_domain(db_obj) if db_obj else None

    def create_with_idempotency(self, payment: Payment) -> tuple:
        """Create payment with idempotency check."""
        existing = self.get_by_idempotency_key(payment.idempotency_key)
        if existing:
            return existing, False

        db_payment = self._to_db(payment)
        self.db.add(db_payment)
        self.db.flush()
        self.db.refresh(db_payment)
        return self._to_domain(db_payment), True


class StateSnapshotRepository(BaseRepository):
    """Repository for StateSnapshot for crash recovery."""

    def __init__(self, db: Session):
        super().__init__(db, db_models.StateSnapshotModel)

    def _to_domain(self, db_obj: db_models.StateSnapshotModel) -> OrderSnapshot:
        return OrderSnapshot(
            id=db_obj.id,
            timestamp=db_obj.timestamp,
            order_id=db_obj.entity_id,
            status=db_obj.state_json.get("status") if db_obj.state_json else None,
            pending_operations=db_obj.state_json.get("pending_operations", []) if db_obj.state_json else [],
            last_processed_event=db_obj.last_event
        )

    def _to_db(self, snapshot: OrderSnapshot) -> db_models.StateSnapshotModel:
        return db_models.StateSnapshotModel(
            id=snapshot.id or str(uuid4()),
            entity_type="order",
            entity_id=snapshot.order_id,
            state_json={
                "status": snapshot.status,
                "pending_operations": snapshot.pending_operations
            },
            timestamp=snapshot.timestamp or utcnow(),
            last_event=snapshot.last_processed_event,
            is_recovery_point=True
        )

    def _get_update_dict(self, snapshot: OrderSnapshot) -> Dict[str, Any]:
        return {
            "entity_type": "order",
            "entity_id": snapshot.order_id,
            "state_json": {
                "status": snapshot.status,
                "pending_operations": snapshot.pending_operations
            },
            "timestamp": snapshot.timestamp or utcnow(),
            "last_event": snapshot.last_processed_event,
            "is_recovery_point": True
        }

    def save_snapshot(self, snapshot: OrderSnapshot) -> OrderSnapshot:
        db_obj = self._to_db(snapshot)
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return self._to_domain(db_obj)

    def get_latest_for_entity(self, entity_type: str, entity_id: str) -> Optional[OrderSnapshot]:
        db_obj = self.db.query(db_models.StateSnapshotModel).filter(
            db_models.StateSnapshotModel.entity_type == entity_type,
            db_models.StateSnapshotModel.entity_id == entity_id
        ).order_by(db_models.StateSnapshotModel.timestamp.desc()).first()
        return self._to_domain(db_obj) if db_obj else None

    def get_recovery_points(self, entity_type: str = "order") -> List[OrderSnapshot]:
        db_objs = self.db.query(db_models.StateSnapshotModel).filter(
            db_models.StateSnapshotModel.entity_type == entity_type,
            db_models.StateSnapshotModel.is_recovery_point == True
        ).all()
        return [self._to_domain(obj) for obj in db_objs]
