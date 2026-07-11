"""
Locust load-test plan for the OMS backend.

Scenarios:
  1. Baseline load — 200 concurrent users, steady state.
  2. Sustained load — 2 000 concurrent users (target concurrency).
  3. Spike test — ramp from 2 000 to 6 000 users in 60 s (3x spike).

Metrics captured (via /metrics endpoint and Locust's built-in stats):
  - p50 / p95 / p99 latency
  - Throughput (RPS)
  - Error rate
  - Queue depth (from rate limiter)
"""

from __future__ import annotations

import random

from locust import FastHttpUser, between, events, task


# ── Test data ──────────────────────────────────────────────────────────

PRODUCT_IDS: list[int] = []
CUSTOMER_IDS: list[int] = []
ORDER_IDS: list[int] = []


class OMSUser(FastHttpUser):
    """Simulates a customer browsing and placing orders."""

    wait_time = between(0.5, 3.0)  # realistic think time

    def on_start(self) -> None:
        """Ensure test data exists."""
        # Create a customer
        resp = self.client.post(
            "/api/v1/customers",
            json={
                "name": f"LoadTestUser_{random.randint(1, 100000)}",
                "address": "123 Test St",
                "phone": "+1-555-0000",
                "banking_details": "ACC-12345",
                "role": "CUSTOMER",
            },
        )
        if resp.status_code == 201:
            self.customer_id = resp.json()["id"]
            CUSTOMER_IDS.append(self.customer_id)
        else:
            self.customer_id = 1  # fallback

        # Ensure some products exist
        if not PRODUCT_IDS:
            for i in range(1, 21):
                r = self.client.post(
                    "/api/v1/products",
                    json={
                        "description": f"Load Test Product {i}",
                        "base_price": round(random.uniform(5.0, 500.0), 2),
                        "currency": "USD",
                        "stock_available": random.randint(10, 1000),
                    },
                )
                if r.status_code == 201:
                    PRODUCT_IDS.append(r.json()["id"])

    @task(3)
    def browse_products(self) -> None:
        """Search/browse products — hot path, p95 ≤ 150 ms."""
        params = {"page": random.randint(1, 5), "page_size": 20}
        if random.random() < 0.3:
            params["q"] = random.choice(["Product", "Test", "Load"])
        self.client.get("/api/v1/products", params=params, name="browse_products")

    @task(2)
    def get_product(self) -> None:
        """Get a single product — hot path."""
        if PRODUCT_IDS:
            pid = random.choice(PRODUCT_IDS)
            self.client.get(f"/api/v1/products/{pid}", name="get_product")

    @task(1)
    def place_order(self) -> None:
        """Place an order — checkout hot path, p95 ≤ 300 ms."""
        if not PRODUCT_IDS:
            return
        num_items = random.randint(1, 3)
        items = []
        for _ in range(num_items):
            pid = random.choice(PRODUCT_IDS)
            items.append({"product_id": pid, "quantity": random.randint(1, 5)})

        with self.client.post(
            "/api/v1/orders",
            json={"customer_id": self.customer_id, "line_items": items},
            name="place_order",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                order_id = resp.json()["id"]
                ORDER_IDS.append(order_id)
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def process_order_workflow(self) -> None:
        """Simulate the full order workflow (back-office steps).

        Version sequence after each step:
          1. Create order   → version=1 (CREATED)
          2. Accept          → version=2 (ACCEPTED)
          3. Create invoice  → version=3 (INVOICED)
          4. Process payment → version=3 (order stays INVOICED, payment PENDING)
          5. Verify payment  → version=4 (PAID)
          6. Ship            → version=5 (SHIPPED)
          7. Close           → version=6 (CLOSED)

        The order's actual total_amount and version are fetched dynamically
        to avoid hardcoded values that would cause validation failures.
        """
        if not ORDER_IDS:
            return
        order_id = random.choice(ORDER_IDS)

        # Fetch the order to get the real total_amount and current version
        order_resp = self.client.get(f"/api/v1/orders/{order_id}", name="get_order_for_workflow")
        if order_resp.status_code != 200:
            return
        order_data = order_resp.json()
        current_version = order_data["version"]
        total_amount = order_data["total_amount"]

        # Step 1: Order Staff accepts (version must be current after creation)
        resp1 = self.client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"new_status": "ACCEPTED", "version": current_version},
            name="accept_order",
        )
        if resp1.status_code != 200:
            return
        current_version += 1

        # Step 2: Accountant creates invoice (version must be current after accept)
        resp2 = self.client.post(
            "/api/v1/invoices",
            json={
                "order_id": order_id,
                "billing_name": "Test Billing",
                "billing_address": "456 Invoice Ave",
                "version": current_version,
            },
            name="create_invoice",
        )
        if resp2.status_code != 201:
            return
        current_version += 1

        # Step 3: Customer pays (version must be current after invoice;
        # order stays INVOICED, version unchanged by process_payment)
        resp3 = self.client.post(
            "/api/v1/payments",
            json={
                "order_id": order_id,
                "amount": total_amount,
                "currency": "USD",
                "method": "CREDIT_CARD",
                "version": current_version,
            },
            name="process_payment",
        )
        if resp3.status_code != 201:
            return
        payment_id = resp3.json()["id"]

        # Step 4: Accountant verifies payment (order transitions to PAID,
        # version becomes current+1)
        resp4 = self.client.post(
            "/api/v1/payments/verify",
            json={
                "payment_id": payment_id,
                "status": "COMPLETED",
                "order_version": current_version,
            },
            name="verify_payment",
        )
        if resp4.status_code != 200:
            return
        current_version += 1

        # Step 5: Order Staff ships (version must be current after verify)
        self.client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"new_status": "SHIPPED", "version": current_version},
            name="ship_order",
        )
        current_version += 1

        # Step 6: Order Staff closes (version must be current after ship)
        self.client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"new_status": "CLOSED", "version": current_version},
            name="close_order",
        )


# ── Scenario configurations ──────────────────────────────────────────

SCENARIOS = {
    "baseline": {
        "users": 200,
        "spawn_rate": 10,
        "run_time": "5m",
    },
    "sustained": {
        "users": 2000,
        "spawn_rate": 50,
        "run_time": "10m",
    },
    "spike": {
        "users": 6000,
        "spawn_rate": 100,  # 6000 users in 60 s
        "run_time": "5m",
    },
}


# ── Event hooks for metrics ──────────────────────────────────────────

@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument(
        "--scenario",
        type=str,
        default="sustained",
        choices=["baseline", "sustained", "spike"],
        help="Load-test scenario to run",
    )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Apply the selected scenario configuration to Locust's runtime settings."""
    scenario_name = environment.parsed_options.scenario
    scenario_cfg = SCENARIOS.get(scenario_name)
    if scenario_cfg is None:
        print(f"Unknown scenario '{scenario_name}', using defaults")
        return

    # Override Locust's runtime settings with scenario values
    environment.runner.run_time = scenario_cfg["run_time"]
    # Note: --users and --spawn-rate are set via CLI args; the scenario
    # config serves as documentation and can be used with:
    #   locust -f load_test/locustfile.py --scenario=sustained --users=2000 --spawn-rate=50
    print(f"Scenario '{scenario_name}' selected: {scenario_cfg}")
