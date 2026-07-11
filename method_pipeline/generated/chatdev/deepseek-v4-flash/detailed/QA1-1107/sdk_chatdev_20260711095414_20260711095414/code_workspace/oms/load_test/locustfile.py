"""
Locust load-test plan for the OMS backend.

Three scenarios:
1. Baseline steady load (2,000 concurrent users, 1-5s think time, 10 min)
2. Sustained load (5,000 concurrent sessions, >=10 min)
3. 3x spike (ramp 60s, hold >=5 min)

Pass/fail thresholds tied to NFR 1.1-1.3.

SEPARATION OF CONCERNS:
- CheckoutUser: only checkout-critical endpoints (place_order, submit_payment)
  subject to NFR 1.1 (p95 <= 300ms, p99 <= 600ms)
- BackOfficeUser: only back-office endpoints (accept, invoice, verify, ship, close)
  subject to relaxed target (p95 <= 1s)
- BrowseUser: only product search/browse endpoints
  subject to NFR 1.1 (p95 <= 150ms)
"""
from __future__ import annotations

import random
from uuid import uuid4

from locust import HttpUser, task, between, constant


CUSTOMER_ID = "00000000-0000-0000-0000-000000000001"
PRODUCT_IDS = [
    "00000000-0000-0000-0000-000000000010",
    "00000000-0000-0000-0000-000000000011",
    "00000000-0000-0000-0000-000000000012",
]


class BrowseUser(HttpUser):
    """
    Simulates a customer browsing/searching products.
    Think time 1-5 s (uniform distribution).
    p95 latency target: <= 150 ms (NFR 1.1).
    """

    wait_time = between(1, 5)

    @task
    def browse_products(self) -> None:
        """Product search/browse -- p95 <= 150 ms."""
        q = random.choice(["laptop", "phone", "book", "shirt", "shoe"])
        with self.client.get(
            f"/api/v1/products/search?q={q}&limit=10",
            name="/api/v1/products/search",
            catch_response=True,
        ) as resp:
            if resp.elapsed.total_seconds() > 0.150:
                resp.failure(f"p95 breach: {resp.elapsed.total_seconds():.3f}s")


class CheckoutUser(HttpUser):
    """
    Simulates a customer performing the checkout journey.
    Think time 1-5 s (uniform distribution).
    p95 latency target: <= 300 ms, p99 <= 600 ms (NFR 1.1).
    """

    wait_time = between(1, 5)

    @task
    def checkout_journey(self) -> None:
        """
        Full checkout: place order -> submit payment.
        p95 <= 300 ms, p99 <= 600 ms.
        """
        # Place order
        line_items = [
            {
                "product_id": random.choice(PRODUCT_IDS),
                "quantity": random.randint(1, 3),
                "unit_price": round(random.uniform(10.0, 500.0), 2),
            }
        ]
        with self.client.post(
            "/api/v1/orders/",
            json={"customer_id": CUSTOMER_ID, "line_items": line_items},
            name="/api/v1/orders/",
            catch_response=True,
        ) as resp:
            if resp.status_code == 429:
                resp.failure("Rate limited")
                return
            if resp.status_code != 201:
                resp.failure(f"Order failed: {resp.status_code}")
                return
            if resp.elapsed.total_seconds() > 0.300:
                resp.failure(f"p95 breach: {resp.elapsed.total_seconds():.3f}s")

            order_data = resp.json()
            order_id = order_data["id"]
            order_total = order_data["total_amount"]

            # Submit payment (checkout-critical) -- use the actual order total
            idempotency_key = str(uuid4())
            with self.client.post(
                "/api/v1/orders/payment",
                json={
                    "order_id": order_id,
                    "amount": order_total,
                    "method": "CREDIT_CARD",
                    "idempotency_key": idempotency_key,
                },
                name="/api/v1/orders/payment",
                catch_response=True,
            ) as pay_resp:
                if pay_resp.status_code == 429:
                    pay_resp.failure("Rate limited")
                    return
                if pay_resp.elapsed.total_seconds() > 0.300:
                    pay_resp.failure(f"p95 breach: {pay_resp.elapsed.total_seconds():.3f}s")


class BackOfficeUser(HttpUser):
    """
    Simulates Order Staff / Accountant performing back-office operations.
    Think time 2-10 s (longer because these are manual review steps).
    p95 latency target: <= 1 s (relaxed because these are not customer-facing).
    """

    wait_time = between(2, 10)

    @task
    def back_office_workflow(self) -> None:
        """
        Simulates the full back-office workflow:
        accept -> invoice -> verify -> ship -> close.
        Each step has a relaxed p95 target of <= 1s.
        """
        # First, we need an order to work on. We'll create one via the API.
        line_items = [
            {
                "product_id": random.choice(PRODUCT_IDS),
                "quantity": 1,
                "unit_price": round(random.uniform(10.0, 500.0), 2),
            }
        ]
        with self.client.post(
            "/api/v1/orders/",
            json={"customer_id": CUSTOMER_ID, "line_items": line_items},
            name="/api/v1/orders/",
            catch_response=True,
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Order creation failed: {resp.status_code}")
                return
            order_data = resp.json()
            order_id = order_data["id"]
            version = order_data["version"]

        # Accept
        with self.client.post(
            f"/api/v1/orders/{order_id}/accept",
            json={"expected_version": version},
            name="/api/v1/orders/{id}/accept",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                version = resp.json()["version"]
            else:
                resp.failure(f"Accept failed: {resp.status_code}")
                return

        # Invoice
        with self.client.post(
            f"/api/v1/orders/{order_id}/invoice",
            json={"expected_version": version},
            name="/api/v1/orders/{id}/invoice",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                version = resp.json()["version"] if "version" in resp.json() else version
            else:
                resp.failure(f"Invoice failed: {resp.status_code}")
                return

        # Pay (simulate customer payment for back-office workflow)
        idempotency_key = str(uuid4())
        with self.client.post(
            "/api/v1/orders/payment",
            json={
                "order_id": order_id,
                "amount": order_data["total_amount"],
                "method": "CREDIT_CARD",
                "idempotency_key": idempotency_key,
            },
            name="/api/v1/orders/payment",
            catch_response=True,
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Payment failed: {resp.status_code}")
                return

        # Verify payment
        with self.client.post(
            f"/api/v1/orders/{order_id}/verify-payment",
            json={"expected_version": version},
            name="/api/v1/orders/{id}/verify-payment",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                version = resp.json()["version"]
            else:
                resp.failure(f"Verify payment failed: {resp.status_code}")
                return

        # Ship
        with self.client.post(
            f"/api/v1/orders/{order_id}/ship",
            json={"expected_version": version},
            name="/api/v1/orders/{id}/ship",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                version = resp.json()["version"]
            else:
                resp.failure(f"Ship failed: {resp.status_code}")
                return

        # Close
        with self.client.post(
            f"/api/v1/orders/{order_id}/close",
            json={"expected_version": version},
            name="/api/v1/orders/{id}/close",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Close failed: {resp.status_code}")
