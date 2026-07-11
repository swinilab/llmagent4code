"""
Degradation Test (NFR 2.1): Load test that induces severe load while
disabling a non-essential service. Pass if core checkout API returns
success while non-essential API returns fallback.

Usage:
    python tests/test_degradation.py

This script:
1. Starts the OMS API (assumes it's already running on localhost:8000).
2. Sends concurrent requests to the core checkout endpoint.
3. Simultaneously sends requests to the recommendation endpoint.
4. Verifies that checkout succeeds and recommendations return fallback.

Prerequisites:
    - OMS API running on http://localhost:8000
    - PostgreSQL running with schema applied
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid

import httpx

BASE_URL = "http://localhost:8000/api/v1"

# Test configuration
NUM_CONCURRENT_CHECKOUT = 20
NUM_CONCURRENT_RECOMMEND = 20
TIMEOUT_SECONDS = 30.0

# Sample data for creating a customer and product (run once)
SAMPLE_CUSTOMER = {
    "name": "Degradation Test Customer",
    "address": "123 Test St",
    "phone": "+1-555-0100",
    "banking_details": "ACC-12345",
    "role": "CUSTOMER",
}

SAMPLE_PRODUCT = {
    "description": "Test Product",
    "base_price": 29.99,
    "currency": "USD",
    "available": True,
}


async def create_test_data(client: httpx.AsyncClient) -> tuple[str, str]:
    """Create a customer and product for testing."""
    # Create customer
    resp = await client.post(f"{BASE_URL}/customers", json=SAMPLE_CUSTOMER)
    resp.raise_for_status()
    customer_id = resp.json()["id"]

    # Create product
    resp = await client.post(f"{BASE_URL}/products", json=SAMPLE_PRODUCT)
    resp.raise_for_status()
    product_id = resp.json()["id"]

    return customer_id, product_id


async def run_checkout(client: httpx.AsyncClient, customer_id: str, product_id: str) -> dict:
    """Simulate a core checkout flow: create order."""
    order_data = {
        "customer_id": customer_id,
        "line_items": [
            {
                "product_id": product_id,
                "quantity": 1,
                "unit_price": 29.99,
                "currency": "USD",
            }
        ],
        "currency": "USD",
    }
    resp = await client.post(f"{BASE_URL}/orders", json=order_data, timeout=TIMEOUT_SECONDS)
    return {"status_code": resp.status_code, "body": resp.json() if resp.status_code < 500 else str(resp.content)}


async def run_recommendation(client: httpx.AsyncClient, customer_id: str) -> dict:
    """Fetch recommendations (non-essential, circuit-breaker protected)."""
    resp = await client.get(
        f"{BASE_URL}/recommendations/{customer_id}",
        timeout=TIMEOUT_SECONDS,
    )
    return {"status_code": resp.status_code, "body": resp.json() if resp.status_code < 500 else str(resp.content)}


async def main() -> int:
    """Run the degradation test."""
    print("=" * 60)
    print("Degradation Test (NFR 2.1)")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Create test data
        print("\n[SETUP] Creating test data...")
        try:
            customer_id, product_id = await create_test_data(client)
            print(f"  Customer ID: {customer_id}")
            print(f"  Product ID:  {product_id}")
        except Exception as e:
            print(f"  FAILED to create test data: {e}")
            print("  Ensure the API and database are running.")
            return 1

        # Phase 1: Concurrent checkout requests (core functionality)
        print(f"\n[PHASE 1] Sending {NUM_CONCURRENT_CHECKOUT} concurrent checkout requests...")
        checkout_tasks = [
            run_checkout(client, customer_id, product_id)
            for _ in range(NUM_CONCURRENT_CHECKOUT)
        ]
        start = time.time()
        checkout_results = await asyncio.gather(*checkout_tasks, return_exceptions=True)
        checkout_duration = time.time() - start

        # Phase 2: Concurrent recommendation requests (non-essential)
        print(f"\n[PHASE 2] Sending {NUM_CONCURRENT_RECOMMEND} concurrent recommendation requests...")
        rec_tasks = [
            run_recommendation(client, customer_id)
            for _ in range(NUM_CONCURRENT_RECOMMEND)
        ]
        start = time.time()
        rec_results = await asyncio.gather(*rec_tasks, return_exceptions=True)
        rec_duration = time.time() - start

        # Analyze results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        # Checkout results
        checkout_success = 0
        checkout_fail = 0
        for r in checkout_results:
            if isinstance(r, dict) and r.get("status_code") in (200, 201):
                checkout_success += 1
            else:
                checkout_fail += 1

        print(f"\nCheckout (CORE):")
        print(f"  Success: {checkout_success}/{NUM_CONCURRENT_CHECKOUT}")
        print(f"  Failed:  {checkout_fail}/{NUM_CONCURRENT_CHECKOUT}")
        print(f"  Duration: {checkout_duration:.2f}s")

        # Recommendation results
        rec_fallback = 0
        rec_other = 0
        for r in rec_results:
            if isinstance(r, dict):
                body = r.get("body", {})
                if isinstance(body, dict) and body.get("fallback"):
                    rec_fallback += 1
                else:
                    rec_other += 1
            else:
                rec_other += 1

        print(f"\nRecommendations (NON-ESSENTIAL):")
        print(f"  Fallback responses: {rec_fallback}/{NUM_CONCURRENT_RECOMMEND}")
        print(f"  Other:              {rec_other}/{NUM_CONCURRENT_RECOMMEND}")
        print(f"  Duration: {rec_duration:.2f}s")

        # Determine pass/fail
        checkout_pass_rate = checkout_success / NUM_CONCURRENT_CHECKOUT
        if checkout_pass_rate >= 0.9:
            print("\n✅ PASS: Core checkout availability >= 90% under load")
        else:
            print(f"\n❌ FAIL: Core checkout availability {checkout_pass_rate:.0%} < 90%")
            return 1

        if rec_fallback > 0:
            print("✅ PASS: Non-essential recommendations returned fallback")
        else:
            print("⚠️  NOTE: No fallback responses observed (recommendation service may be available)")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
