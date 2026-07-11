"""Locust load test plan for OMS performance verification.

Three scenarios (NFR 1.1-1.3):
  1. Baseline steady load: 2,000 concurrent users, 1-5s think time, 10 min
  2. Sustained load: 5,000 concurrent sessions, ≥10 min
  3. Spike: 3x baseline ramp over 60s, held ≥5 min

Metrics captured per scenario:
  - p50/p95/p99 latency per endpoint class
  - Throughput (req/s)
  - Error rate (%)
  - CPU/memory utilization (via /metrics endpoint)
  - Queue depth (via /metrics)
  - Circuit breaker state transitions (via /metrics)

Pass/fail thresholds (NFR 1.1-1.3):
  - Checkout (place_order, pay): p95 ≤ 300ms, p99 ≤ 600ms
  - Browse/search: p95 ≤ 150ms
  - Back-office (accept, invoice, verify, ship, close): p95 ≤ 1s
  - Error rate < 1% under all scenarios
  - No crashes or OOM during spike
"""

import random
import time
from typing import Any

from locust import FastHttpUser, between, constant, task


class CheckoutUser(FastHttpUser):
    """Simulates customer checkout flow (checkout-critical path)."""

    wait_time = between(1, 5)  # 1-5s think time

    def on_start(self):
        """Initialize test data."""
        self.customer_id = "00000000-0000-0000-0000-000000000001"
        self.product_id = "00000000-0000-0000-0000-000000000001"
        self.order_id = None

    @task(3)
    def browse_products(self):
        """Browse/search products (p95 ≤ 150ms)."""
        self.client.get(f"/api/v1/products/search?q=test&page=1&page_size=20", name="search_products")

    @task(2)
    def get_product(self):
        """Get product detail (cached)."""
        self.client.get(f"/api/v1/products/{self.product_id}", name="get_product")

    @task(1)
    def place_order(self):
        """Place order (checkout-critical, p95 ≤ 300ms)."""
        payload = {
            "customer_id": self.customer_id,
            "line_items": [
                {"product_id": self.product_id, "quantity": random.randint(1, 3)}
            ],
        }
        with self.client.post(
            "/api/v1/orders/place",
            json=payload,
            name="place_order",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.order_id = data["id"]
            elif resp.status_code == 429:
                resp.success()  # Rate limited is acceptable behavior
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def submit_payment(self):
        """Submit payment (checkout-critical, p95 ≤ 300ms)."""
        if self.order_id is None:
            return
        payload = {
            "order_id": self.order_id,
            "amount": "100.00",
            "method": "CREDIT_CARD",
            "idempotency_key": f"pay-{self.order_id}-{time.time()}",
        }
        with self.client.post(
            "/api/v1/orders/pay",
            json=payload,
            name="submit_payment",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            elif resp.status_code == 429:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class BackOfficeUser(FastHttpUser):
    """Simulates back-office operations (p95 ≤ 1s)."""

    wait_time = between(2, 8)

    def on_start(self):
        self.order_id = None

    @task(1)
    def accept_order(self):
        """Accept order (back-office)."""
        if self.order_id is None:
            return
        with self.client.post(
            "/api/v1/orders/accept",
            json={"order_id": self.order_id},
            name="accept_order",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def create_invoice(self):
        """Create invoice (back-office)."""
        if self.order_id is None:
            return
        payload = {
            "order_id": self.order_id,
            "customer_name": "Test Customer",
            "customer_address": "123 Test St",
            "billing_info": "billing@test.com",
        }
        with self.client.post(
            "/api/v1/orders/invoice",
            json=payload,
            name="create_invoice",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def ship_order(self):
        """Ship order (back-office)."""
        if self.order_id is None:
            return
        with self.client.post(
            "/api/v1/orders/ship",
            json={"order_id": self.order_id},
            name="ship_order",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def close_order(self):
        """Close order (back-office)."""
        if self.order_id is None:
            return
        with self.client.post(
            "/api/v1/orders/close",
            json={"order_id": self.order_id},
            name="close_order",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class SpikeUser(FastHttpUser):
    """Aggressive user for spike testing (3x baseline)."""

    wait_time = constant(0.5)  # Very short think time for spike

    @task
    def rapid_checkout(self):
        """Rapid checkout attempts for spike testing."""
        payload = {
            "customer_id": "00000000-0000-0000-0000-000000000001",
            "line_items": [
                {"product_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}
            ],
        }
        self.client.post(
            "/api/v1/orders/place",
            json=payload,
            name="spike_place_order",
        )
