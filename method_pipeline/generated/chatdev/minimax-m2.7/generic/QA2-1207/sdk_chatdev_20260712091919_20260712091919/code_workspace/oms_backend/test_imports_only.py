#!/usr/bin/env python3
"""Test script to verify OMS backend functionality"""
import sys
import os

# Add oms_backend to path
sys.path.insert(0, '/home/swe/llmagent4code/method_pipeline/generated/chatdev/minimax-m2.7/generic/QA2-1207/sdk_chatdev_20260712091919_20260712091919/code_workspace/oms_backend')

# Now test imports
try:
    from src.domain.models import (
        Customer, Order, Product, Payment, Invoice, LineItem,
        Address, OrderStatus, PaymentStatus, InvoiceStatus, UserRole
    )
    print("✓ Domain models imported successfully")
except Exception as e:
    print(f"✗ Failed to import domain models: {e}")
    sys.exit(1)

try:
    from src.infrastructure.database import SessionLocal, init_db, engine
    print("✓ Database module imported successfully")
except Exception as e:
    print(f"✗ Failed to import database module: {e}")
    sys.exit(1)

try:
    from src.infrastructure.repositories import (
        CustomerRepository, OrderRepository, ProductRepository,
        PaymentRepository, InvoiceRepository
    )
    print("✓ Repositories imported successfully")
except Exception as e:
    print(f"✗ Failed to import repositories: {e}")
    sys.exit(1)

try:
    from src.services.customer_service import CustomerService
    from src.services.product_service import ProductService
    from src.services.order_service import OrderService
    from src.services.invoice_service import InvoiceService
    from src.services.payment_service import PaymentService
    print("✓ Services imported successfully")
except Exception as e:
    print(f"✗ Failed to import services: {e}")
    sys.exit(1)

try:
    from src.utils.resilience import (
        CircuitBreaker, CircuitBreakerConfig, FeatureFlags, StateManager, HealthChecker,
        CircuitState, CircuitBreakerOpen
    )
    print("✓ Resilience utilities imported successfully")
except Exception as e:
    print(f"✗ Failed to import resilience utilities: {e}")
    sys.exit(1)

# Test feature flags
try:
    flags = FeatureFlags()
    assert flags.is_enabled("analytics_enabled") is True
    flags.disable_non_essential()
    assert flags.is_enabled("analytics_enabled") is False
    print("✓ Feature flags work correctly")
except Exception as e:
    print(f"✗ Feature flags test failed: {e}")
    sys.exit(1)

# Test circuit breaker
try:
    cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60))
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    print("✓ Circuit breaker works correctly")
except Exception as e:
    print(f"✗ Circuit breaker test failed: {e}")
    sys.exit(1)

# Test state manager
try:
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    try:
        state_mgr = StateManager(snapshot_dir=temp_dir)
        state = {"order_id": "test-123", "status": "pending"}
        snapshot_id = state_mgr.save_snapshot("order", "test-123", state, "test_event")
        assert snapshot_id is not None
        retrieved = state_mgr.get_snapshot("order", "test-123")
        assert retrieved is not None
        assert retrieved["state"]["order_id"] == "test-123"
        print("✓ State manager works correctly")
    finally:
        shutil.rmtree(temp_dir)
except Exception as e:
    print(f"✗ State manager test failed: {e}")
    sys.exit(1)

# Test database initialization
try:
    init_db()
    session = SessionLocal()
    session.close()
    print("✓ Database initialization works correctly")
except Exception as e:
    print(f"✗ Database initialization test failed: {e}")
    sys.exit(1)

print("\n✓ All imports and basic tests passed!")
