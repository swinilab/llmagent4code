"""
OMS Backend Tests - Testing the complete workflow and NFR compliance.
"""
import pytest
import os
import sys
import time
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.models import (
    Customer, Order, Product, Payment, Invoice, LineItem,
    Address, OrderStatus, PaymentStatus, InvoiceStatus, UserRole
)
from src.infrastructure.database import SessionLocal, init_db, engine
from src.infrastructure.repositories import (
    CustomerRepository, OrderRepository, ProductRepository,
    PaymentRepository, InvoiceRepository
)
from src.services.customer_service import CustomerService
from src.services.product_service import ProductService
from src.services.order_service import OrderService
from src.services.invoice_service import InvoiceService
from src.services.payment_service import PaymentService
from src.utils.resilience import (
    CircuitBreaker, CircuitBreakerConfig, FeatureFlags, StateManager, HealthChecker,
    CircuitState, CircuitBreakerOpen
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_address():
    return Address(
        street="123 Main St",
        city="New York",
        state="NY",
        postal_code="10001",
        country="USA"
    )


@pytest.fixture
def sample_customer(db_session, sample_address):
    service = CustomerService(db_session)
    customer = service.create_customer(
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        address=sample_address,
        role=UserRole.CUSTOMER
    )
    return customer


@pytest.fixture
def sample_product(db_session):
    service = ProductService(db_session)
    product = service.create_product(
        sku="PROD-001",
        description="Test Product",
        base_price=99.99,
        currency="USD",
        stock_quantity=100
    )
    return product


class TestCustomerService:
    """Test customer service operations."""

    def test_create_customer(self, db_session, sample_address):
        service = CustomerService(db_session)
        customer = service.create_customer(
            name="Jane Doe",
            email="jane@example.com",
            phone="+0987654321",
            address=sample_address
        )
        assert customer.id is not None
        assert customer.name == "Jane Doe"
        assert customer.email == "jane@example.com"
        assert customer.role == UserRole.CUSTOMER

    def test_get_customer(self, db_session, sample_customer):
        service = CustomerService(db_session)
        found = service.get_customer(sample_customer.id)
        assert found is not None
        assert found.id == sample_customer.id

    def test_update_customer(self, db_session, sample_customer):
        service = CustomerService(db_session)
        updated = service.update_customer(sample_customer.id, name="John Updated")
        assert updated.name == "John Updated"


class TestProductService:
    """Test product service operations."""

    def test_create_product(self, db_session):
        service = ProductService(db_session)
        product = service.create_product(
            sku="NEW-SKU",
            description="New Product",
            base_price=49.99,
            stock_quantity=50
        )
        assert product.id is not None
        assert product.sku == "NEW-SKU"
        assert product.is_active is True

    def test_update_stock(self, db_session, sample_product):
        service = ProductService(db_session)
        updated = service.update_stock(sample_product.id, 10)
        assert updated.stock_quantity == 110


class TestOrderWorkflow:
    """Test complete order workflow (Steps 1-7)."""

    def test_complete_workflow(self, db_session, sample_customer, sample_product, sample_address):
        """Test the complete order -> payment -> shipping -> closure workflow."""
        
        # Step 1: Customer places order
        order_service = OrderService(db_session)
        line_items = [
            LineItem(
                product_id=sample_product.id,
                product_description=sample_product.description,
                quantity=2,
                unit_price=sample_product.base_price,
                currency="USD"
            )
        ]
        
        order = order_service.place_order(
            customer_id=sample_customer.id,
            line_items=line_items,
            shipping_address=sample_address,
            idempotency_key=str(uuid4())
        )
        assert order.status == OrderStatus.PENDING
        assert order.total > 0

        # Step 2: Order Staff accepts order
        order = order_service.accept_order(order.id)
        assert order.status == OrderStatus.ACCEPTED
        assert order.accepted_at is not None

        # Step 3: Accountant creates invoice
        invoice_service = InvoiceService(db_session)
        invoice = invoice_service.create_invoice(
            order_id=order.id,
            customer_id=sample_customer.id,
            billing_address=sample_address,
            due_date_days=30
        )
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.total == order.total

        # Issue invoice
        invoice = invoice_service.issue_invoice(invoice.id)
        assert invoice.status == InvoiceStatus.ISSUED

        # Update order status
        order = order_service.mark_invoiced(order.id, invoice.id)
        assert order.status == OrderStatus.INVOICED

        # Step 4: Customer pays invoice
        payment_service = PaymentService(db_session)
        payment = payment_service.create_payment(
            order_id=order.id,
            invoice_id=invoice.id,
            customer_id=sample_customer.id,
            amount=invoice.total,
            method="bank_transfer"
        )
        assert payment.status == PaymentStatus.PENDING

        # Process payment
        payment = payment_service.process_payment(payment.id)
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.transaction_ref is not None

        # Step 5: Accountant verifies payment
        payment = payment_service.verify_payment(payment.id)
        assert payment.status == PaymentStatus.COMPLETED

        # Update order status
        order = order_service.mark_paid(order.id)
        assert order.status == OrderStatus.PAID

        # Step 6: Order Staff ships paid order
        order = order_service.ship_order(order.id, tracking_number="TRACK-123")
        assert order.status == OrderStatus.SHIPPED
        assert order.shipped_at is not None

        # Step 7: Order Staff closes completed order
        order = order_service.close_order(order.id)
        assert order.status == OrderStatus.COMPLETED
        assert order.completed_at is not None


class TestGracefulDegradation:
    """Test NFR 2.1 Graceful Degradation."""

    def test_feature_flags(self):
        """Test feature flags can disable non-essential features."""
        flags = FeatureFlags()
        
        # All enabled by default
        assert flags.is_enabled("analytics_enabled") is True
        
        # Disable non-essential
        flags.disable_non_essential()
        assert flags.is_enabled("analytics_enabled") is False
        assert flags.is_enabled("notifications_enabled") is False
        
        # Re-enable all
        flags.enable_all()
        assert flags.is_enabled("analytics_enabled") is True

    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60))
        
        # Record failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_circuit_breaker_half_open(self):
        """Test circuit breaker transitions to half-open."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1))
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True


class TestFaultDetection:
    """Test NFR 2.2 Fault Detection and Recovery."""

    def test_health_checker(self):
        """Test health checker monitors components."""
        checker = HealthChecker()
        
        healthy_count = [0]
        def healthy_fn():
            healthy_count[0] += 1
            return True
        
        checker.register_component("test_service", healthy_fn)
        result = checker.check_health("test_service")
        
        assert result["status"] == "healthy"
        assert healthy_count[0] == 1

    def test_health_checker_unhealthy(self):
        """Test health checker detects unhealthy component."""
        checker = HealthChecker()
        failure_count = [0]
        
        def failing_fn():
            failure_count[0] += 1
            if failure_count[0] >= 2:
                return True
            return False
        
        checker.register_component("failing_service", failing_fn)
        
        # First check - should be unhealthy
        result1 = checker.check_health("failing_service")
        assert result1["status"] == "unhealthy"
        
        # Second check - should recover to healthy
        result2 = checker.check_health("failing_service")
        assert result2["status"] == "healthy"


class TestStatePreservation:
    """Test NFR 2.3 State Preservation."""

    def test_idempotency_key(self, db_session, sample_customer, sample_product, sample_address):
        """Test idempotency key prevents duplicate orders."""
        order_service = OrderService(db_session)
        idempotency_key = str(uuid4())
        
        line_items = [
            LineItem(
                product_id=sample_product.id,
                product_description=sample_product.description,
                quantity=1,
                unit_price=sample_product.base_price
            )
        ]
        
        # First request
        order1 = order_service.place_order(
            customer_id=sample_customer.id,
            line_items=line_items,
            shipping_address=sample_address,
            idempotency_key=idempotency_key
        )
        
        # Second request with same idempotency key should return same order
        order2 = order_service.place_order(
            customer_id=sample_customer.id,
            line_items=line_items,
            shipping_address=sample_address,
            idempotency_key=idempotency_key
        )
        
        assert order1.id == order2.id

    def test_state_manager_snapshots(self):
        """Test state manager saves and retrieves snapshots."""
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        try:
            state_mgr = StateManager(snapshot_dir=temp_dir)
            
            # Save a snapshot
            state = {"order_id": "test-123", "status": "pending"}
            snapshot_id = state_mgr.save_snapshot("order", "test-123", state, "test_event")
            
            assert snapshot_id is not None
            
            # Retrieve snapshot
            retrieved = state_mgr.get_snapshot("order", "test-123")
            assert retrieved is not None
            assert retrieved["state"]["order_id"] == "test-123"
            
            # Clear snapshot
            state_mgr.clear_snapshot("order", "test-123")
            assert state_mgr.get_snapshot("order", "test-123") is None
        finally:
            shutil.rmtree(temp_dir)


class TestOrderServiceWorkflow:
    """Test order service workflow transitions."""

    def test_invalid_workflow_transition(self, db_session, sample_customer, sample_product, sample_address):
        """Test that invalid workflow transitions raise errors."""
        order_service = OrderService(db_session)
        
        line_items = [
            LineItem(
                product_id=sample_product.id,
                product_description=sample_product.description,
                quantity=1,
                unit_price=sample_product.base_price
            )
        ]
        
        order = order_service.place_order(
            customer_id=sample_customer.id,
            line_items=line_items,
            shipping_address=sample_address
        )
        
        # Try to ship before accepting - should fail
        from src.services.order_service import OrderWorkflowError
        with pytest.raises(OrderWorkflowError):
            order_service.ship_order(order.id)


class TestDatabaseHealth:
    """Test database health and WAL mode."""

    def test_wal_mode_enabled(self):
        """Test that WAL mode is enabled for crash safety."""
        from src.infrastructure.database import check_db_health
        
        health = check_db_health()
        assert health["status"] == "healthy"
        assert health.get("wal_mode") == "wal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
