"""
Load test script for the OMS (NFR 1.1, NFR 1.2, NFR 1.3).

This script performs:
  1. Baseline load test (normal traffic)
  2. Sustained concurrency test (2,000 concurrent users)
  3. Spike test (3x traffic spike within 60 seconds)

Metrics collected:
  - p50/p95/p99 latency
  - Throughput (requests/second)
  - Error rate
  - Resource utilization (via /health endpoints)

Usage:
  python load_test.py [--base-url http://localhost:8000] [--duration 60]

Requires: pip install httpx
"""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


@dataclass
class Metrics:
    """Collected performance metrics."""
    latencies: list[float] = field(default_factory=list)
    errors: int = 0
    total: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def p50(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies) * 1000  # ms

    @property
    def p95(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lats = sorted(self.latencies)
        idx = int(len(sorted_lats) * 0.95)
        return sorted_lats[idx] * 1000  # ms

    @property
    def p99(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lats = sorted(self.latencies)
        idx = int(len(sorted_lats) * 0.99)
        return sorted_lats[idx] * 1000  # ms

    @property
    def throughput(self) -> float:
        duration = self.end_time - self.start_time
        if duration <= 0:
            return 0.0
        return self.total / duration

    @property
    def error_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.errors / self.total) * 100


async def _create_customer(client: httpx.AsyncClient) -> str:
    """Create a test customer and return their ID."""
    resp = await client.post(
        f"{BASE_URL}{API_PREFIX}/customers",
        json={"name": f"TestUser_{int(time.time())}"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def _create_product(client: httpx.AsyncClient) -> str:
    """Create a test product and return its ID."""
    resp = await client.post(
        f"{BASE_URL}{API_PREFIX}/products",
        json={
            "name": f"TestProduct_{int(time.time())}",
            "price_amount": 19.99,
            "stock": 100,
        },
    )
    resp.raise_for_status()
    return resp.json()["id"]


async def _checkout(client: httpx.AsyncClient, customer_id: str, product_id: str) -> float:
    """Simulate a checkout and return latency in seconds."""
    start = time.monotonic()
    resp = await client.post(
        f"{BASE_URL}{API_PREFIX}/orders",
        json={
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": 1}],
        },
    )
    elapsed = time.monotonic() - start
    if resp.status_code >= 400:
        raise ValueError(f"Checkout failed: {resp.status_code} {resp.text}")
    return elapsed


async def _browse_products(client: httpx.AsyncClient) -> float:
    """Browse products and return latency in seconds."""
    start = time.monotonic()
    resp = await client.get(f"{BASE_URL}{API_PREFIX}/products")
    elapsed = time.monotonic() - start
    if resp.status_code >= 400:
        raise ValueError(f"Browse failed: {resp.status_code} {resp.text}")
    return elapsed


async def _run_user_session(
    client: httpx.AsyncClient,
    customer_id: str,
    product_id: str,
    metrics: Metrics,
    session_type: str = "checkout",
) -> None:
    """Run a single user session."""
    try:
        if session_type == "checkout":
            latency = await _checkout(client, customer_id, product_id)
        else:
            latency = await _browse_products(client)
        metrics.latencies.append(latency)
    except Exception as exc:
        metrics.errors += 1
        logger.debug("Request error: %s", exc)
    finally:
        metrics.total += 1


async def _run_concurrent_users(
    num_users: int,
    duration: float,
    session_type: str = "checkout",
) -> Metrics:
    """Run concurrent user sessions for a given duration."""
    metrics = Metrics()
    metrics.start_time = time.monotonic()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create shared test data
        customer_id = await _create_customer(client)
        product_id = await _create_product(client)

        end_time = time.monotonic() + duration
        all_tasks: list[asyncio.Task] = []

        while time.monotonic() < end_time:
            # Launch a batch of concurrent users
            batch = [
                asyncio.create_task(
                    _run_user_session(client, customer_id, product_id, metrics, session_type)
                )
                for _ in range(num_users)
            ]
            all_tasks.extend(batch)
            await asyncio.sleep(0.1)  # Throttle to avoid overwhelming

        # Wait for ALL tasks to complete before recording end_time
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)

    metrics.end_time = time.monotonic()
    return metrics


async def _run_spike_test(
    base_users: int,
    spike_multiplier: int,
    spike_duration: float,
) -> Metrics:
    """Run a spike test: 3x traffic spike within 60 seconds."""
    metrics = Metrics()
    metrics.start_time = time.monotonic()

    async with httpx.AsyncClient(timeout=30.0) as client:
        customer_id = await _create_customer(client)
        product_id = await _create_product(client)

        all_tasks: list[asyncio.Task] = []

        # Phase 1: Baseline (30 seconds)
        logger.info("Spike test: Phase 1 — Baseline (%d users)", base_users)
        phase1_end = time.monotonic() + 30
        while time.monotonic() < phase1_end:
            batch = [
                asyncio.create_task(
                    _run_user_session(client, customer_id, product_id, metrics, "checkout")
                )
                for _ in range(base_users)
            ]
            all_tasks.extend(batch)
            await asyncio.sleep(0.5)

        # Phase 2: Spike (3x traffic, spike_duration seconds)
        spike_users = base_users * spike_multiplier
        logger.info("Spike test: Phase 2 — Spike (%d users)", spike_users)
        phase2_end = time.monotonic() + spike_duration
        while time.monotonic() < phase2_end:
            batch = [
                asyncio.create_task(
                    _run_user_session(client, customer_id, product_id, metrics, "checkout")
                )
                for _ in range(spike_users)
            ]
            all_tasks.extend(batch)
            await asyncio.sleep(0.2)

        # Phase 3: Recovery (30 seconds)
        logger.info("Spike test: Phase 3 — Recovery (%d users)", base_users)
        phase3_end = time.monotonic() + 30
        while time.monotonic() < phase3_end:
            batch = [
                asyncio.create_task(
                    _run_user_session(client, customer_id, product_id, metrics, "checkout")
                )
                for _ in range(base_users)
            ]
            all_tasks.extend(batch)
            await asyncio.sleep(0.5)

        # Wait for ALL tasks to complete before recording end_time
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)

    metrics.end_time = time.monotonic()
    return metrics


async def _check_health() -> dict:
    """Check the health of the system."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health/ready")
        return resp.json()


async def main():
    """Run all load tests."""
    logger.info("=" * 60)
    logger.info("OMS Load Test Suite")
    logger.info("=" * 60)

    # Check health first
    health = await _check_health()
    logger.info("System health: %s", json.dumps(health, indent=2))

    # Test 1: Baseline checkout (100 concurrent users, 30 seconds)
    logger.info("\n--- Test 1: Baseline Checkout (100 users, 30s) ---")
    metrics1 = await _run_concurrent_users(100, 30.0, "checkout")
    logger.info("Results:")
    logger.info("  Total requests: %d", metrics1.total)
    logger.info("  Errors: %d (%.2f%%)", metrics1.errors, metrics1.error_rate)
    logger.info("  Throughput: %.2f req/s", metrics1.throughput)
    logger.info("  p50 latency: %.2f ms", metrics1.p50)
    logger.info("  p95 latency: %.2f ms", metrics1.p95)
    logger.info("  p99 latency: %.2f ms", metrics1.p99)

    # Test 2: Browse products (200 concurrent users, 30 seconds)
    logger.info("\n--- Test 2: Browse Products (200 users, 30s) ---")
    metrics2 = await _run_concurrent_users(200, 30.0, "browse")
    logger.info("Results:")
    logger.info("  Total requests: %d", metrics2.total)
    logger.info("  Errors: %d (%.2f%%)", metrics2.errors, metrics2.error_rate)
    logger.info("  Throughput: %.2f req/s", metrics2.throughput)
    logger.info("  p50 latency: %.2f ms", metrics2.p50)
    logger.info("  p95 latency: %.2f ms", metrics2.p95)
    logger.info("  p99 latency: %.2f ms", metrics2.p99)

    # Test 3: Sustained concurrency (2,000 concurrent users, 60 seconds)
    logger.info("\n--- Test 3: Sustained Concurrency (2,000 users, 60s) ---")
    metrics3 = await _run_concurrent_users(2000, 60.0, "checkout")
    logger.info("Results:")
    logger.info("  Total requests: %d", metrics3.total)
    logger.info("  Errors: %d (%.2f%%)", metrics3.errors, metrics3.error_rate)
    logger.info("  Throughput: %.2f req/s", metrics3.throughput)
    logger.info("  p50 latency: %.2f ms", metrics3.p50)
    logger.info("  p95 latency: %.2f ms", metrics3.p95)
    logger.info("  p99 latency: %.2f ms", metrics3.p99)

    # Test 4: Spike test (3x traffic spike)
    logger.info("\n--- Test 4: Spike Test (3x spike, 60s) ---")
    metrics4 = await _run_spike_test(100, 3, 60.0)
    logger.info("Results:")
    logger.info("  Total requests: %d", metrics4.total)
    logger.info("  Errors: %d (%.2f%%)", metrics4.errors, metrics4.error_rate)
    logger.info("  Throughput: %.2f req/s", metrics4.throughput)
    logger.info("  p50 latency: %.2f ms", metrics4.p50)
    logger.info("  p95 latency: %.2f ms", metrics4.p95)
    logger.info("  p99 latency: %.2f ms", metrics4.p99)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Load Test Summary")
    logger.info("=" * 60)
    logger.info("Test 1 (Baseline Checkout): p95=%.2fms, throughput=%.2f req/s, errors=%.2f%%",
                metrics1.p95, metrics1.throughput, metrics1.error_rate)
    logger.info("Test 2 (Browse Products):  p95=%.2fms, throughput=%.2f req/s, errors=%.2f%%",
                metrics2.p95, metrics2.throughput, metrics2.error_rate)
    logger.info("Test 3 (Sustained 2K):     p95=%.2fms, throughput=%.2f req/s, errors=%.2f%%",
                metrics3.p95, metrics3.throughput, metrics3.error_rate)
    logger.info("Test 4 (Spike 3x):        p95=%.2fms, throughput=%.2f req/s, errors=%.2f%%",
                metrics4.p95, metrics4.throughput, metrics4.error_rate)

    # Pass/fail thresholds (NFR 1.1)
    passed = 0
    total_tests = 4
    if metrics1.p95 <= 300:
        logger.info("PASS: Checkout p95 (%.2fms) <= 300ms", metrics1.p95)
        passed += 1
    else:
        logger.warning("FAIL: Checkout p95 (%.2fms) > 300ms", metrics1.p95)
    if metrics2.p95 <= 150:
        logger.info("PASS: Browse p95 (%.2fms) <= 150ms", metrics2.p95)
        passed += 1
    else:
        logger.warning("FAIL: Browse p95 (%.2fms) > 150ms", metrics2.p95)
    if metrics3.error_rate < 1.0:
        logger.info("PASS: Sustained concurrency error rate (%.2f%%) < 1%%", metrics3.error_rate)
        passed += 1
    else:
        logger.warning("FAIL: Sustained concurrency error rate (%.2f%%) >= 1%%", metrics3.error_rate)
    if metrics4.error_rate < 5.0:
        logger.info("PASS: Spike test error rate (%.2f%%) < 5%%", metrics4.error_rate)
        passed += 1
    else:
        logger.warning("FAIL: Spike test error rate (%.2f%%) >= 5%%", metrics4.error_rate)

    logger.info("\nPassed %d/%d tests", passed, total_tests)
    return 0 if passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
