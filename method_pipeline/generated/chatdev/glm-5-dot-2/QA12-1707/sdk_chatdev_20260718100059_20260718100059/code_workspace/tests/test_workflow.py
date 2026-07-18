"""End-to-end integration test for the OMS backend.

Tests the complete workflow:
1. Create customer + product
2. Customer places order
3. Order staff accepts order
4. Accountant creates invoice
5. Customer pays invoice
6. Accountant verifies payment
7. Order staff ships order
8. Order staff closes order

Run with: uv run pytest tests/test_workflow.py -v
"""
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from oms.main import create_app
from oms.database import dispose_db


@pytest_asyncio.fixture(scope="function")
async def client():
    """Create a test client with a fresh database."""
    import oms.config as config_module
    config_module.settings.database_url = "sqlite+aiosqlite:///./test_oms.db"
    config_module.settings.db_echo = False

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac

    await dispose_db()
    for f in ["./test_oms.db", "./test_oms.db-wal", "./test_oms.db-shm"]:
        if os.path.exists(f):
            os.remove(f)


@pytest.mark.asyncio
async def test_full_workflow(client: AsyncClient):
    """Test the complete order lifecycle from creation to closure."""
    # Step 0: Health check
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"

    # Step 1: Create a customer
    resp = await client.post("/api/v1/customers/", json={
        "name": "Alice Customer",
        "address": "123 Main St, Springfield",
        "phone": "+15551234567",
        "banking_details": {"iban": "DE89370400440532013000", "bank_name": "Test Bank"},
        "role": "customer",
    })
    assert resp.status_code == 201, resp.text
    customer_id = resp.json()["id"]

    # Step 2: Create a product
    resp = await client.post("/api/v1/products/", json={
        "description": "Wireless Headphones",
        "base_price": 99.99,
        "currency": "USD",
    })
    assert resp.status_code == 201, resp.text
    product_id = resp.json()["id"]

    # Step 3: Customer places order
    resp = await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 2}],
    })
    assert resp.status_code == 201, resp.text
    order = resp.json()
    order_id = order["id"]
    assert order["status"] == "pending"
    assert order["subtotal"] == 199.98
    assert order["total"] > order["subtotal"]

    # Step 4: Order staff accepts order
    resp = await client.post(f"/api/v1/orders/{order_id}/transition", json={
        "status": "accepted",
    })
    assert resp.status_code == 200, resp.text
    order = resp.json()
    assert order["status"] == "accepted"
    assert order["accepted_at"] is not None

    # Step 5: Accountant creates invoice
    resp = await client.post("/api/v1/invoices/", json={
        "order_id": order_id,
    })
    assert resp.status_code == 201, resp.text
    invoice = resp.json()
    invoice_id = invoice["id"]
    assert invoice["status"] == "issued"

    # Verify order is now INVOICED
    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.json()["status"] == "invoiced"

    # Step 6: Customer pays invoice
    resp = await client.post("/api/v1/payments/", json={
        "order_id": order_id,
        "amount": invoice["total"],
        "method": "credit_card",
    })
    assert resp.status_code == 201, resp.text
    payment = resp.json()
    payment_id = payment["id"]
    assert payment["status"] == "pending"

    # Step 7: Accountant verifies payment
    resp = await client.post(f"/api/v1/payments/{payment_id}/verify", json={
        "verified": True,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "verified"

    # Verify order is now PAID
    resp = await client.get(f"/api/v1/orders/{order_id}")
    assert resp.json()["status"] == "paid"

    # Verify invoice is now PAID
    resp = await client.get(f"/api/v1/invoices/{invoice_id}")
    assert resp.json()["status"] == "paid"

    # Step 8: Order staff ships order
    resp = await client.post(f"/api/v1/orders/{order_id}/transition", json={
        "status": "shipped",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "shipped"

    # Step 9: Order staff closes order
    resp = await client.post(f"/api/v1/orders/{order_id}/transition", json={
        "status": "closed",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_invalid_transition(client: AsyncClient):
    """Test that invalid status transitions are rejected."""
    resp = await client.post("/api/v1/customers/", json={
        "name": "Bob Buyer", "address": "456 Oak Ave", "phone": "15559876543",
        "name": "Bob Buyer", "address": "456 Oak Ave", "phone": "15559876543",
    })
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/products/", json={
        "description": "USB Cable", "base_price": 15.00, "currency": "USD",
    })
    product_id = resp.json()["id"]

    resp = await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    order_id = resp.json()["id"]

    # Try to ship a PENDING order (invalid)
    resp = await client.post(f"/api/v1/orders/{order_id}/transition", json={
        "status": "shipped",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_product_search(client: AsyncClient):
    """Test product search functionality."""
    await client.post("/api/v1/products/", json={
        "description": "Gaming Laptop", "base_price": 1500.00, "currency": "USD",
    })
    await client.post("/api/v1/products/", json={
        "description": "Office Laptop", "base_price": 800.00, "currency": "USD",
    })
    await client.post("/api/v1/products/", json={
        "description": "Wireless Mouse", "base_price": 25.00, "currency": "USD",
    })

    resp = await client.get("/api/v1/products/search?q=laptop")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

    resp = await client.get("/api/v1/products/search?min_price=500&max_price=1000")
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_customer_order_history(client: AsyncClient):
    """Test that customer order history is returned."""
    resp = await client.post("/api/v1/customers/", json={
        "name": "Carol Shopper", "address": "789 Pine Rd", "phone": "15551112222",
    })
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/products/", json={
        "description": "Test Product", "base_price": 10.00, "currency": "USD",
    })
    product_id = resp.json()["id"]

    await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 3}],
    })

    resp = await client.get(f"/api/v1/customers/{customer_id}")
    assert resp.status_code == 200
    assert len(resp.json()["orders"]) == 2

@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    """Test the readiness probe."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_payment_circuit_open_returns_503(client: AsyncClient):
    """When the payment-gateway circuit breaker is OPEN, payment creation
    must return a graceful 503 (NFR 2.2) instead of an unhandled 500."""
    from oms.core.resilience import circuit_breaker_registry, CircuitState

    # --- build an order up to the INVOICED state so payment is allowed ---
    resp = await client.post("/api/v1/customers/", json={
        "name": "Dana Pay", "address": "1 Pay St", "phone": "+15550001111",
    })
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/products/", json={
        "description": "Keyboard", "base_price": 50.00, "currency": "USD",
    })
    product_id = resp.json()["id"]

    resp = await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    order_id = resp.json()["id"]

    await client.post(f"/api/v1/orders/{order_id}/transition", json={"status": "accepted"})
    resp = await client.post("/api/v1/invoices/", json={"order_id": order_id})
    invoice_total = resp.json()["total"]

    # --- force the payment_gateway breaker OPEN ---
    breaker = circuit_breaker_registry.get_or_create("payment_gateway")
    breaker._state = CircuitState.OPEN
    breaker._last_failure_time = float("inf")  # keep it open (no cooldown elapsed)

    resp = await client.post("/api/v1/payments/", json={
        "order_id": order_id,
        "amount": invoice_total,
        "method": "credit_card",
    })

    # Restore breaker state regardless of assertion outcome
    breaker.reset()

    assert resp.status_code == 503, resp.text
    assert "circuit open" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_dispose_clears_factory():
    """dispose_db() must clear BOTH the engine and the module-level
    async_session_factory so the get_session() guard fires cleanly after
    disposal (NFR 2.3 State Preservation / restart invariant)."""
    import oms.database as d

    await d.init_db()
    assert d.async_session_factory is not None
    assert d.engine is not None

    await d.dispose_db()
    assert d.engine is None
    assert d.async_session_factory is None  # the bug: was NOT cleared before fix

    # The get_session() guard must now raise the intended clean message rather
    # than attempting to open a session on a disposed engine.
    with pytest.raises(RuntimeError, match="Database not initialised"):
        async for _ in d.get_session():
            pass


@pytest.mark.asyncio
async def test_mixed_currency_order_rejected(client: AsyncClient):
    """Regression: an order that mixes products of different currencies must
    be rejected with HTTP 400 rather than silently persisting a meaningless
    subtotal/total. Locks in the single-currency order invariant enforced by
    OrderService._resolve_line_items."""
    resp = await client.post("/api/v1/customers/", json={
        "name": "Eve Mixed", "address": "10 Currency St", "phone": "+15552223333",
    })
    assert resp.status_code == 201, resp.text
    customer_id = resp.json()["id"]

    resp = await client.post("/api/v1/products/", json={
        "description": "USD Widget", "base_price": 99.99, "currency": "USD",
    })
    assert resp.status_code == 201, resp.text
    usd_product_id = resp.json()["id"]

    resp = await client.post("/api/v1/products/", json={
        "description": "EUR Widget", "base_price": 50.00, "currency": "EUR",
    })
    assert resp.status_code == 201, resp.text
    eur_product_id = resp.json()["id"]

    # Order containing both a USD and an EUR product must be rejected.
    resp = await client.post("/api/v1/orders/", json={
        "customer_id": customer_id,
        "items": [
            {"product_id": usd_product_id, "quantity": 1},
            {"product_id": eur_product_id, "quantity": 1},
        ],
    })
    assert resp.status_code == 400, resp.text
    assert "currency" in resp.json()["detail"].lower()