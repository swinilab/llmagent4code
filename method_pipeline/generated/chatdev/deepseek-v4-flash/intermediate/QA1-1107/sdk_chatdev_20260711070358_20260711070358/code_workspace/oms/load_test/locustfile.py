"""
Locust load test for the Order Management System.
Measures p50/p95/p99 latency, throughput, error rate under various load scenarios.

Usage:
    # Step 1: Seed test data
    python -m oms.load_test.seed_data

    # Step 2: Run load test
    locust -f oms/load_test/locustfile.py --host=http://localhost:8000

Scenarios:
    1. Baseline: 500 concurrent users, steady state
    2. Sustained: 2000 concurrent users (target for NFR 1.1)
    3. Spike: 6000 concurrent users (3x baseline, NFR 1.3)
"""
import asyncio
import json
import os
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# Path to store seeded IDs so workers can share them
_SEED_FILE = os.path.join(os.path.dirname(__file__), ".seed_data.json")


def _load_seed_data() -> dict:
    """Load seeded customer and product IDs from a shared file."""
    if os.path.exists(_SEED_FILE):
        with open(_SEED_FILE, "r") as f:
            return json.load(f)
    return {"customer_ids": [], "product_ids": []}


def _save_seed_data(data: dict) -> None:
    """Save seeded IDs to a shared file for worker processes."""
    with open(_SEED_FILE, "w") as f:
        json.dump(data, f)


class OMSUser(HttpUser):
    """
    Simulates a customer interacting with the OMS.
    Uses realistic think times between actions.
    """
    wait_time = between(1, 5)  # Realistic think time distribution

    # Shared seed data loaded once per worker
    _seeded_customer_ids: list[str] = []
    _seeded_product_ids: list[str] = []

    def on_start(self):
        """Initialize user state with real seeded data."""
        self.customer_id = None
        self.order_id = None
        self.product_ids = []
        self.order_version = 1

        # Load seed data if not already loaded for this worker
        if not OMSUser._seeded_customer_ids:
            seed = _load_seed_data()
            OMSUser._seeded_customer_ids = seed.get("customer_ids", [])
            OMSUser._seeded_product_ids = seed.get("product_ids", [])

    @task(3)
    def browse_products(self):
        """Browse/search products - latency-sensitive (NFR 1.1: p95 <= 150 ms)."""
        query = random.choice(["", "widget", "gadget", "tool", "device"])
        with self.client.get(
            f"/api/v1/products?q={query}&limit=20",
            name="browse_products",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data:
                    self.product_ids = [p["id"] for p in data[:5]]
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def checkout_journey(self):
        """
        Full checkout journey: create order.
        This is the critical path (NFR 1.1: p95 <= 300 ms).
        """
        if not OMSUser._seeded_product_ids or not OMSUser._seeded_customer_ids:
            return

        product_id = random.choice(OMSUser._seeded_product_ids)
        customer_id = random.choice(OMSUser._seeded_customer_ids)

        payload = {
            "customer_id": customer_id,
            "line_items": [
                {
                    "product_id": product_id,
                    "product_description": "Load Test Product",
                    "quantity": random.randint(1, 3),
                    "unit_price": "19.99",
                    "currency": "USD",
                }
            ],
        }

        with self.client.post(
            "/api/v1/orders",
            json=payload,
            name="checkout_create_order",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.order_id = data["id"]
                self.order_version = data["version"]
                response.success()
            elif response.status_code == 429:
                response.success()  # Rate limited - acceptable behavior
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def get_order(self):
        """Get order details."""
        if not self.order_id:
            return
        with self.client.get(
            f"/api/v1/orders/{self.order_id}",
            name="get_order",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/api/v1/health", name="health_check")


class SpikeTestUser(HttpUser):
    """
    Simulates a traffic spike scenario (3x baseline).
    Used for NFR 1.3 verification.
    """
    wait_time = between(0.1, 0.5)  # Faster requests for spike

    _seeded_customer_ids: list[str] = []
    _seeded_product_ids: list[str] = []

    def on_start(self):
        if not SpikeTestUser._seeded_customer_ids:
            seed = _load_seed_data()
            SpikeTestUser._seeded_customer_ids = seed.get("customer_ids", [])
            SpikeTestUser._seeded_product_ids = seed.get("product_ids", [])

    @task
    def rapid_checkout(self):
        """Rapid order creation to simulate spike."""
        if not SpikeTestUser._seeded_customer_ids or not SpikeTestUser._seeded_product_ids:
            return

        payload = {
            "customer_id": random.choice(SpikeTestUser._seeded_customer_ids),
            "line_items": [
                {
                    "product_id": random.choice(SpikeTestUser._seeded_product_ids),
                    "product_description": "Spike Test Product",
                    "quantity": 1,
                    "unit_price": "10.00",
                    "currency": "USD",
                }
            ],
        }
        with self.client.post(
            "/api/v1/orders",
            json=payload,
            name="spike_create_order",
            catch_response=True,
        ) as response:
            if response.status_code in (201, 429):
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


# Custom event hooks for metrics capture
@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize test environment - seed data if running in master mode."""
    if isinstance(environment.runner, MasterRunner):
        # Master process: seed data and share IDs with workers
        from oms.load_test.seed_data import seed_test_data

        result = asyncio.run(seed_test_data(num_customers=1000, num_products=100))
        _save_seed_data({
            "customer_ids": result["customer_ids"],
            "product_ids": result["product_ids"],
        })
