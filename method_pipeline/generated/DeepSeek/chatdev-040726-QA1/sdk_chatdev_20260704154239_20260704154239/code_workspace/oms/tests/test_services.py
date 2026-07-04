"""
Unit tests for all service layers using an in-memory SQLite database.

Fixtures are defined in conftest.py and shared across test modules.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.order import OrderCreate, OrderItemCreate, OrderStatusUpdate
from app.schemas.payment import PaymentCreate
from app.schemas.invoice import InvoiceCreate, InvoiceStatusUpdate
from app.services.customer_service import CustomerService
from app.services.product_service import ProductService
from app.services.order_service import OrderService, OrderStateError
from app.services.payment_service import PaymentService, PaymentStateError
from app.services.invoice_service import InvoiceService, InvoiceStateError
from app.services.workflow_service import WorkflowService, WorkflowError


# ---------------------------------------------------------------------------
# CustomerService Tests
# ---------------------------------------------------------------------------

class TestCustomerService:
    def test_create(self, db: Session, customer_data: CustomerCreate):
        customer = CustomerService.create(db, customer_data)
        assert customer.id is not None
        assert customer.name == "Test User"
        assert customer.role == "customer"

    def test_get_by_id(self, db: Session, sample_customer: Customer):
        found = CustomerService.get_by_id(db, sample_customer.id)
        assert found is not None
        assert found.id == sample_customer.id

    def test_get_by_id_not_found(self, db: Session):
        assert CustomerService.get_by_id(db, "nonexistent") is None

    def test_list_all(self, db: Session, sample_customer: Customer):
        customers = CustomerService.list_all(db)
        assert len(customers) >= 1

    def test_update(self, db: Session, sample_customer: Customer):
        updated = CustomerService.update(db, sample_customer.id, CustomerUpdate(name="Updated Name"))
        assert updated is not None
        assert updated.name == "Updated Name"

    def test_delete(self, db: Session, sample_customer: Customer):
        assert CustomerService.delete(db, sample_customer.id) is True
        assert CustomerService.get_by_id(db, sample_customer.id) is None


# ---------------------------------------------------------------------------
# ProductService Tests
# ---------------------------------------------------------------------------

class TestProductService:
    def test_create(self, db: Session, product_data: ProductCreate):
        product = ProductService.create(db, product_data)
        assert product.id is not None
        assert product.base_price == 19.99

    def test_search(self, db: Session, sample_product: Product):
        results = ProductService.search(db, query="Test")
        assert len(results) >= 1
        results = ProductService.search(db, query="Nonexistent")
        assert len(results) == 0

    def test_update(self, db: Session, sample_product: Product):
        updated = ProductService.update(db, sample_product.id, ProductUpdate(base_price=9.99))
        assert updated is not None
        assert updated.base_price == 9.99


# ---------------------------------------------------------------------------
# OrderService Tests
# ---------------------------------------------------------------------------

class TestOrderService:
    def test_create(self, db: Session, sample_customer: Customer, sample_product: Product):
        data = OrderCreate(
            customer_id=sample_customer.id,
            line_items=[
                OrderItemCreate(product_id=sample_product.id, quantity=1, unit_price=19.99)
            ],
        )
        order = OrderService.create(db, data)
        assert order.id is not None
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == 19.99

    def test_get_by_id_eager_loads_line_items(self, db: Session, sample_order: Order):
        """Verify that joinedload eagerly fetches line_items (NFR 1.1)."""
        order = OrderService.get_by_id(db, sample_order.id)
        assert order is not None
        # Accessing line_items should not trigger an additional query
        # because it was eager-loaded. We just verify the data is present.
        assert len(order.line_items) == 1
        assert order.line_items[0].quantity == 2

    def test_update_status_valid(self, db: Session, sample_order: Order):
        updated = OrderService.update_status(
            db, sample_order.id, OrderStatusUpdate(status=OrderStatus.ACCEPTED)
        )
        assert updated is not None
        assert updated.status == OrderStatus.ACCEPTED

    def test_update_status_invalid(self, db: Session, sample_order: Order):
        with pytest.raises(OrderStateError):
            OrderService.update_status(
                db, sample_order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED)
            )

    def test_update_status_skip_validation(self, db: Session, sample_order: Order):
        """skip_validation=True bypasses the direct-transition safety net."""
        updated = OrderService.update_status(
            db, sample_order.id, OrderStatusUpdate(status=OrderStatus.SHIPPED), skip_validation=True
        )
        assert updated is not None
        assert updated.status == OrderStatus.SHIPPED


# ---------------------------------------------------------------------------
# PaymentService Tests
# ---------------------------------------------------------------------------

class TestPaymentService:
    def test_create(self, db: Session, sample_order: Order):
        data = PaymentCreate(
            order_id=sample_order.id,
            amount=39.98,
            currency="USD",
            method=PaymentMethod.CREDIT_CARD,
        )
        payment = PaymentService.create(db, data)
        assert payment.id is not None
        assert payment.status == PaymentStatus.PENDING

    def test_mark_paid(self, db: Session, sample_order: Order):
        data = PaymentCreate(
            order_id=sample_order.id, amount=39.98, currency="USD", method=PaymentMethod.CREDIT_CARD
        )
        payment = PaymentService.create(db, data)
        paid = PaymentService.mark_paid(db, payment.id)
        assert paid is not None
        assert paid.status == PaymentStatus.PAID
        assert paid.paid_at is not None

    def test_verify(self, db: Session, sample_order: Order):
        data = PaymentCreate(
            order_id=sample_order.id, amount=39.98, currency="USD", method=PaymentMethod.CREDIT_CARD
        )
        payment = PaymentService.create(db, data)
        PaymentService.mark_paid(db, payment.id)
        verified = PaymentService.verify(db, payment.id)
        assert verified is not None
        assert verified.status == PaymentStatus.VERIFIED

    def test_verify_without_paid_fails(self, db: Session, sample_order: Order):
        data = PaymentCreate(
            order_id=sample_order.id, amount=39.98, currency="USD", method=PaymentMethod.CREDIT_CARD
        )
        payment = PaymentService.create(db, data)
        with pytest.raises(PaymentStateError):
            PaymentService.verify(db, payment.id)


# ---------------------------------------------------------------------------
# InvoiceService Tests
# ---------------------------------------------------------------------------

class TestInvoiceService:
    def test_create(self, db: Session, sample_order: Order):
        data = InvoiceCreate(
            order_id=sample_order.id,
            billing_info="Test billing info",
            amount=39.98,
            currency="USD",
        )
        invoice = InvoiceService.create(db, data)
        assert invoice.id is not None
        assert invoice.status == InvoiceStatus.DRAFT

    def test_issue(self, db: Session, sample_order: Order):
        data = InvoiceCreate(
            order_id=sample_order.id, billing_info="Test", amount=39.98, currency="USD"
        )
        invoice = InvoiceService.create(db, data)
        issued = InvoiceService.issue(db, invoice.id)
        assert issued is not None
        assert issued.status == InvoiceStatus.ISSUED
        assert issued.issue_date is not None
        assert issued.due_date is not None

    def test_issue_non_draft_fails(self, db: Session, sample_order: Order):
        data = InvoiceCreate(
            order_id=sample_order.id, billing_info="Test", amount=39.98, currency="USD"
        )
        invoice = InvoiceService.create(db, data)
        InvoiceService.issue(db, invoice.id)
        with pytest.raises(InvoiceStateError):
            InvoiceService.issue(db, invoice.id)


# ---------------------------------------------------------------------------
# WorkflowService Tests (full lifecycle)
# ---------------------------------------------------------------------------

class TestWorkflowService:
    def test_full_lifecycle(self, db: Session, sample_customer: Customer, sample_product: Product):
        """Execute the complete 7-step workflow and verify each transition."""
        # Step 1: Place order
        order_data = OrderCreate(
            customer_id=sample_customer.id,
            line_items=[
                OrderItemCreate(product_id=sample_product.id, quantity=1, unit_price=19.99)
            ],
        )
        order = OrderService.create(db, order_data)
        assert order.status == OrderStatus.PENDING

        # Step 2: Accept
        order = WorkflowService.accept_order(db, order.id)
        assert order.status == OrderStatus.ACCEPTED

        # Step 3: Create invoice
        invoice = WorkflowService.create_invoice_for_order(
            db, order.id, billing_info="Invoice for test"
        )
        assert invoice.status == InvoiceStatus.ISSUED
        order = OrderService.get_by_id(db, order.id)
        assert order.status == OrderStatus.INVOICED
        assert order.invoice_ref == invoice.id

        # Step 4: Pay invoice
        payment = WorkflowService.pay_invoice(db, invoice.id, "credit_card")
        assert payment.status == PaymentStatus.PAID
        order = OrderService.get_by_id(db, order.id)
        assert order.status == OrderStatus.PAID

        # Step 5: Verify payment
        payment = WorkflowService.verify_payment(db, payment.id)
        assert payment.status == PaymentStatus.VERIFIED
        order = OrderService.get_by_id(db, order.id)
        assert order.status == OrderStatus.VERIFIED

        # Step 6: Ship
        order = WorkflowService.ship_order(db, order.id)
        assert order.status == OrderStatus.SHIPPED

        # Step 7: Close
        order = WorkflowService.close_order(db, order.id)
        assert order.status == OrderStatus.CLOSED

    def test_invalid_transition(self, db: Session, sample_order: Order):
        """Attempting an out-of-order transition should raise WorkflowError."""
        with pytest.raises(WorkflowError):
            WorkflowService.ship_order(db, sample_order.id)
