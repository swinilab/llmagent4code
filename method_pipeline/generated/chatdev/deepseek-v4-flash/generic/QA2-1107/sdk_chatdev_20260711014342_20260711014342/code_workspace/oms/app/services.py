"""
Service layer - business logic, transaction boundaries, cross-cutting orchestration.
Each method is a self-contained unit of work with clear pre/post conditions.
"""
from __future__ import annotations

from datetime import timedelta
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
from app.infrastructure import (
    append_event,
    checkout_circuit,
    invoice_circuit,
    payment_circuit,
    shipping_circuit,
)
from app.repositories import (
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
)


# ======================================================================
# Customer Service
# ======================================================================
class CustomerService:
    def __init__(self, session: Session):
        self._session = session
        self._repo = CustomerRepository(session)

    def register(self, name: str, address: str, phone: str, banking_details: str, role: UserRole) -> Customer:
        customer = Customer(
            name=name,
            address=address,
            phone=phone,
            banking_details=banking_details,
            role=role,
        )
        return self._repo.create(customer)

    def get(self, customer_id: UUID) -> Optional[Customer]:
        return self._repo.get_by_id(customer_id)

    def list_all(self) -> list[Customer]:
        return self._repo.list_all()


# ======================================================================
# Product Service
# ======================================================================
class ProductService:
    def __init__(self, session: Session):
        self._session = session
        self._repo = ProductRepository(session)

    def create(self, description: str, base_price: Decimal, currency: str) -> Product:
        product = Product(
            description=description,
            base_price=base_price,
            currency=currency,
        )
        return self._repo.create(product)

    def get(self, product_id: UUID) -> Optional[Product]:
        return self._repo.get_by_id(product_id)

    def list_all(self) -> list[Product]:
        return self._repo.list_all()


# ======================================================================
# Order Service
# ======================================================================
class OrderService:
    def __init__(self, session: Session):
        self._session = session
        self._order_repo = OrderRepository(session)
        self._customer_repo = CustomerRepository(session)
        self._product_repo = ProductRepository(session)
        self._payment_repo = PaymentRepository(session)
        self._invoice_repo = InvoiceRepository(session)

    def place_order(self, customer_id: UUID, items: list[dict]) -> Order:
        """Step 1: Customer places an order. Core checkout - uses checkout circuit."""

        # ---- Validate customer exists before creating order ----
        customer = self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        # -------------------------------------------------------

        # ---- Validate every referenced product exists ---------
        for item in items:
            product_id = UUID(item["product_id"])
            product = self._product_repo.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
        # -------------------------------------------------------

        def _place():
            line_items = [
                LineItem(
                    product_id=UUID(item["product_id"]),
                    quantity=item["quantity"],
                    unit_price=Decimal(str(item["unit_price"])),
                    currency=item.get("currency", "USD"),
                )
                for item in items
            ]
            order = Order(
                customer_id=customer_id,
                line_items=line_items,
                status=OrderStatus.PENDING,
            )
            created = self._order_repo.create(order)
            append_event(
                self._session,
                "Order",
                str(created.id),
                "OrderPlaced",
                {
                    "order_id": str(created.id),
                    "customer_id": str(customer_id),
                    "line_items": [
                        {
                            "id": str(li.id),
                            "product_id": str(li.product_id),
                            "quantity": li.quantity,
                            "unit_price": str(li.unit_price),
                            "currency": li.currency,
                        }
                        for li in line_items
                    ],
                },
            )
            return created

        return checkout_circuit.call(_place)

    # ---- Order Staff actions ----

    def accept_order(self, order_id: UUID) -> Optional[Order]:
        """Step 2: Order Staff reviews and accepts a pending order."""
        order = self._order_repo.get_by_id(order_id)
        if not order:
            return None
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot accept order in status {order.status.value}")

        updated = self._order_repo.update_status(order_id, OrderStatus.ACCEPTED)
        append_event(
            self._session,
            "Order",
            str(order_id),
            "OrderAccepted",
            {"order_id": str(order_id)},
        )
        return updated

    def ship_order(self, order_id: UUID) -> Optional[Order]:
        """Step 6: Order Staff ships a paid order."""

        def _ship():
            order = self._order_repo.get_by_id(order_id)
            if not order:
                return None
            if order.status != OrderStatus.PAID:
                raise ValueError(f"Cannot ship order in status {order.status.value}")
            updated = self._order_repo.update_status(order_id, OrderStatus.SHIPPED)
            append_event(
                self._session,
                "Order",
                str(order_id),
                "OrderShipped",
                {"order_id": str(order_id)},
            )
            return updated

        return shipping_circuit.call(_ship)

    def close_order(self, order_id: UUID) -> Optional[Order]:
        """Step 7: Order Staff closes a completed (shipped) order."""
        order = self._order_repo.get_by_id(order_id)
        if not order:
            return None
        if order.status != OrderStatus.SHIPPED:
            raise ValueError(f"Cannot close order in status {order.status.value}")
        updated = self._order_repo.update_status(order_id, OrderStatus.CLOSED)
        append_event(
            self._session,
            "Order",
            str(order_id),
            "OrderClosed",
            {"order_id": str(order_id)},
        )
        return updated

    def cancel_order(self, order_id: UUID) -> Optional[Order]:
        """Cancel an order that is still PENDING or ACCEPTED."""
        order = self._order_repo.get_by_id(order_id)
        if not order:
            return None
        if order.status not in (OrderStatus.PENDING, OrderStatus.ACCEPTED):
            raise ValueError(f"Cannot cancel order in status {order.status.value}")
        updated = self._order_repo.update_status(order_id, OrderStatus.CANCELLED)
        append_event(
            self._session,
            "Order",
            str(order_id),
            "OrderCancelled",
            {"order_id": str(order_id)},
        )
        return updated

    # ---- Accountant actions ----

    def create_invoice(self, order_id: UUID, billing_name: str, billing_address: str, due_days: int) -> Optional[Invoice]:
        """Step 3: Accountant creates an invoice for an accepted order."""

        def _create_invoice():
            order = self._order_repo.get_by_id(order_id)
            if not order:
                return None
            if order.status != OrderStatus.ACCEPTED:
                raise ValueError(f"Cannot invoice order in status {order.status.value}")

            invoice = Invoice(
                order_id=order_id,
                billing_name=billing_name,
                billing_address=billing_address,
                total_amount=order.total_amount,
                issue_date=utcnow(),
                due_date=utcnow() + timedelta(days=due_days),
                status=InvoiceStatus.ISSUED,
            )
            created = self._invoice_repo.create(invoice)
            self._order_repo.update_invoice_ref(order_id, created.id)
            self._order_repo.update_status(order_id, OrderStatus.INVOICED)
            append_event(
                self._session,
                "Order",
                str(order_id),
                "OrderInvoiced",
                {"order_id": str(order_id), "invoice_id": str(created.id)},
            )
            return created

        return invoice_circuit.call(_create_invoice)

    def record_payment(self, order_id: UUID, amount: Decimal, currency: str, method: PaymentMethod) -> Optional[Payment]:
        """Step 4: Customer pays the invoice (recorded by the system)."""

        def _record_payment():
            order = self._order_repo.get_by_id(order_id)
            if not order:
                return None
            if order.status != OrderStatus.INVOICED:
                raise ValueError(f"Cannot pay order in status {order.status.value}")

            payment = Payment(
                order_id=order_id,
                amount=amount,
                currency=currency,
                method=method,
                status=PaymentStatus.PENDING,
            )
            created = self._payment_repo.create(payment)
            self._order_repo.update_payment_ref(order_id, created.id)
            append_event(
                self._session,
                "Payment",
                str(created.id),
                "PaymentRecorded",
                {
                    "payment_id": str(created.id),
                    "order_id": str(order_id),
                    "amount": str(amount),
                    "currency": currency,
                    "method": method.value,
                },
            )
            return created

        return payment_circuit.call(_record_payment)

    def verify_payment(self, payment_id: UUID, verified: bool = True) -> Optional[Payment]:
        """Step 5: Accountant verifies a payment."""

        def _verify_payment():
            payment = self._payment_repo.get_by_id(payment_id)
            if not payment:
                return None
            if payment.status != PaymentStatus.PENDING:
                raise ValueError(f"Payment already {payment.status.value}")

            if verified:
                updated = self._payment_repo.update_status(payment_id, PaymentStatus.VERIFIED)
                self._order_repo.update_status(payment.order_id, OrderStatus.PAID)
                self._invoice_repo.update_status_by_order_id(payment.order_id, InvoiceStatus.PAID)
                append_event(
                    self._session,
                    "Order",
                    str(payment.order_id),
                    "OrderPaid",
                    {"order_id": str(payment.order_id), "payment_id": str(payment_id)},
                )
            else:
                updated = self._payment_repo.update_status(payment_id, PaymentStatus.FAILED)
                append_event(
                    self._session,
                    "Payment",
                    str(payment_id),
                    "PaymentVerificationFailed",
                    {"payment_id": str(payment_id), "order_id": str(payment.order_id)},
                )
            return updated

        return payment_circuit.call(_verify_payment)

    # ---- Queries ----

    def get_order(self, order_id: UUID) -> Optional[Order]:
        return self._order_repo.get_by_id(order_id)

    def list_orders(self, status: Optional[OrderStatus] = None) -> list[Order]:
        return self._order_repo.list_by_status(status)

    def get_payment(self, payment_id: UUID) -> Optional[Payment]:
        return self._payment_repo.get_by_id(payment_id)

    def get_invoice(self, invoice_id: UUID) -> Optional[Invoice]:
        return self._invoice_repo.get_by_id(invoice_id)

    def get_invoice_by_order(self, order_id: UUID) -> Optional[Invoice]:
        return self._invoice_repo.get_by_order_id(order_id)
