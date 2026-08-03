"""ASR-A1 (timeout), ASR-A2 (retry), ASR-A3 (degradation), ASR-A4 (transactions)."""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from tests.conftest import BASE_URL, advance_to_paid, make_product, metrics

CACHE_TTL_SECONDS = 5
PROXY = "/proxies/postgres"


# --------------------------------------------------------------------------
# ASR-A1 - Dependency timeout detection
# --------------------------------------------------------------------------


def test_asra1_timeout_detection(client: httpx.Client, toxiproxy: httpx.Client) -> None:
    """Latency far above the per-attempt limit yields a bounded 503/504."""
    product = make_product(client, amount="12.34")
    product_id = product["id"]
    client.post("/internal/test/reset")  # ensure the read is uncached

    # Inject latency far exceeding DB_OPERATION_TIMEOUT_MS so no attempt can
    # complete within its time limit.
    toxiproxy.post(
        f"{PROXY}/toxics",
        json={
            "name": "asra1_latency",
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": 5000, "jitter": 0},
        },
    )
    try:
        started = time.monotonic()
        response = client.get(f"/api/v1/products/{product_id}", timeout=20.0)
        elapsed = time.monotonic() - started

        # Total client response time stays bounded well inside 4.5 seconds.
        assert elapsed <= 4.5, f"request took {elapsed:.2f}s, exceeding the 4.5s budget"
        assert response.status_code in (503, 504), response.text
        assert response.json()["error"]["code"] == "DEPENDENCY_TIMEOUT"

        counters = metrics(client)
        assert counters["timeouts_total"] > 0

        # The application remains live throughout.
        assert client.get("/health/live").status_code == 200
    finally:
        toxiproxy.delete(f"{PROXY}/toxics/asra1_latency")

    # Service resumes normally once the fault is removed.
    time.sleep(1.0)
    assert client.get(f"/api/v1/products/{product_id}").status_code == 200


def test_asra1_no_request_hangs_beyond_budget(client: httpx.Client, toxiproxy: httpx.Client) -> None:
    """Under sustained latency, no request exceeds the 4.5-second budget."""
    product = make_product(client, amount="12.34")
    client.post("/internal/test/reset")

    toxiproxy.post(
        f"{PROXY}/toxics",
        json={
            "name": "asra1_latency_multi",
            "type": "latency",
            "stream": "downstream",
            "attributes": {"latency": 5000, "jitter": 0},
        },
    )
    try:
        durations: list[float] = []
        for _ in range(3):
            client.post("/internal/test/reset")
            started = time.monotonic()
            client.get(f"/api/v1/products/{uuid.uuid4()}", timeout=20.0)
            durations.append(time.monotonic() - started)
        hanging = [d for d in durations if d > 4.5]
        assert not hanging, f"{len(hanging)} requests hung beyond 4.5s: {durations}"
    finally:
        toxiproxy.delete(f"{PROXY}/toxics/asra1_latency_multi")


# --------------------------------------------------------------------------
# ASR-A2 - Recovery from transient database faults
# --------------------------------------------------------------------------


def test_asra2_retry_recovers_after_two_transient_faults(client: httpx.Client) -> None:
    """Two injected transient faults, third attempt succeeds, counters exact."""
    product = make_product(client, amount="42.42")
    product_id = product["id"]
    client.post("/internal/test/reset")

    before = metrics(client)
    response = client.get(
        f"/api/v1/products/{product_id}",
        headers={"X-Test-Fault": "transient-db-failures=2"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == product_id

    after = metrics(client)
    # Three attempts entered the real Product read boundary: two injected
    # failures plus the successful third.
    assert after["db_product_read_attempts_total"] - before["db_product_read_attempts_total"] == 3
    # Two of those were retries (attempts after the initial one).
    assert after["retry_attempts_total"] - before["retry_attempts_total"] == 2


def test_asra2_attempts_never_exceed_max(client: httpx.Client) -> None:
    """More injected faults than DB_MAX_ATTEMPTS stops at the limit, no looping."""
    product = make_product(client, amount="42.42")
    client.post("/internal/test/reset")

    response = client.get(
        f"/api/v1/products/{product['id']}",
        headers={"X-Test-Fault": "transient-db-failures=10"},
        timeout=20.0,
    )
    # The bounded policy gives up rather than retrying forever.
    assert response.status_code in (503, 504)
    counters = metrics(client)
    assert counters["db_product_read_attempts_total"] == 3, "attempts exceeded DB_MAX_ATTEMPTS"
    assert counters["retry_attempts_total"] == 2


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/api/v1/products/not-a-uuid", 400),
        (f"/api/v1/products/{uuid.uuid4()}", 404),
    ],
)
def test_asra2_non_transient_failures_are_not_retried(
    client: httpx.Client, path: str, expected: int
) -> None:
    """Malformed requests and unknown IDs never increase retry_attempts_total."""
    client.post("/internal/test/reset")
    assert client.get(path).status_code == expected
    assert metrics(client)["retry_attempts_total"] == 0


def test_asra2_workflow_conflict_is_not_retried(client: httpx.Client) -> None:
    """A 409 workflow conflict is a domain outcome, not a retryable fault."""
    from tests.conftest import make_order

    _, _, order = make_order(client)
    client.post("/internal/test/reset")
    assert client.post(f"/api/v1/orders/{order['id']}/ship").status_code == 409
    assert metrics(client)["retry_attempts_total"] == 0


# --------------------------------------------------------------------------
# ASR-A3 - Graceful degradation during database outage
# --------------------------------------------------------------------------


def test_asra3_graceful_degradation_during_outage(
    client: httpx.Client, toxiproxy: httpx.Client
) -> None:
    """Warmed reads survive a long outage; unwarmed reads and writes fail safely."""
    warmed = make_product(client, amount="11.11")
    unwarmed = make_product(client, amount="22.22")
    customer_product = make_product(client, amount="33.33")

    client.post("/internal/test/reset")
    # Warm exactly one Product; the other is never read through the API.
    assert client.get(f"/api/v1/products/{warmed['id']}").status_code == 200

    # Outage lasts far longer than CACHE_TTL_SECONDS.
    outage_seconds = CACHE_TTL_SECONDS * 3
    toxiproxy.post(PROXY, json={"enabled": False})
    try:
        warmed_successes = 0
        warmed_attempts = 0
        warmed_latencies: list[float] = []
        unhandled_500s = 0

        deadline = time.monotonic() + outage_seconds
        unwarmed_codes: list[tuple[int, str | None]] = []
        write_codes: list[tuple[int, str | None]] = []

        while time.monotonic() < deadline:
            started = time.monotonic()
            response = client.get(f"/api/v1/products/{warmed['id']}", timeout=15.0)
            warmed_latencies.append((time.monotonic() - started) * 1000.0)
            warmed_attempts += 1
            if response.status_code == 200:
                warmed_successes += 1
            elif response.status_code == 500:
                unhandled_500s += 1

            # A Product never read before has no copy to degrade to.
            unwarmed_response = client.get(f"/api/v1/products/{unwarmed['id']}", timeout=15.0)
            code = (
                unwarmed_response.json().get("error", {}).get("code")
                if unwarmed_response.status_code in (503, 504)
                else None
            )
            unwarmed_codes.append((unwarmed_response.status_code, code))
            if unwarmed_response.status_code == 500:
                unhandled_500s += 1

            # State-changing requests require durable state and must fail safely.
            create = client.post(
                "/api/v1/products",
                json={"description": "Outage product", "price": {"amount": "9.99", "currency": "USD"}},
                timeout=15.0,
            )
            create_code = (
                create.json().get("error", {}).get("code")
                if create.status_code in (503, 504)
                else None
            )
            write_codes.append((create.status_code, create_code))
            if create.status_code == 500:
                unhandled_500s += 1

            time.sleep(0.3)

        # Warmed read capability remains available throughout the outage.
        success_rate = warmed_successes / warmed_attempts
        assert success_rate >= 0.99, f"warmed read success rate {success_rate:.4f} < 0.99"

        warmed_latencies.sort()
        p95 = warmed_latencies[int(len(warmed_latencies) * 0.95)]
        assert p95 <= 200.0, f"warmed read p95 {p95:.1f}ms > 200ms"

        # Unwarmed reads surface dependency unavailability, not a timeout code.
        for status, code in unwarmed_codes:
            assert status in (503, 504), f"unwarmed read returned {status}"
            assert code == "DEPENDENCY_UNAVAILABLE", f"unwarmed read carried code {code}"

        # No write reports success.
        for status, code in write_codes:
            assert status == 503, f"write during outage returned {status}"
            assert code == "DEPENDENCY_UNAVAILABLE"

        assert unhandled_500s == 0, f"{unhandled_500s} unhandled 500 responses during the outage"

        # Observation infrastructure stays available during the outage.
        assert client.get("/health/live").status_code == 200
        assert client.get("/internal/metrics").status_code == 200
        # Readiness accurately reports the unready state, and still answers.
        assert client.get("/health/ready").status_code == 503
    finally:
        toxiproxy.post(PROXY, json={"enabled": True})

    # Normal service resumes automatically within 10 seconds.
    recovery_deadline = time.monotonic() + 10.0
    recovered = False
    while time.monotonic() < recovery_deadline:
        if client.get("/health/ready").status_code == 200:
            recovered = True
            break
        time.sleep(0.5)
    recovery_time = 10.0 - (recovery_deadline - time.monotonic())
    assert recovered, "service did not recover within 10 seconds"

    # Post-recovery functional smoke test.
    assert client.get(f"/api/v1/products/{unwarmed['id']}").status_code == 200
    fresh = client.post(
        "/api/v1/products",
        json={"description": "Post recovery product", "price": {"amount": "1.23", "currency": "USD"}},
    )
    assert fresh.status_code == 201


def test_asra3_state_changing_workflow_transitions_fail_safely(
    client: httpx.Client, toxiproxy: httpx.Client
) -> None:
    """Workflow transitions, not just creations, return 503 during an outage."""
    from tests.conftest import make_order

    _, _, order = make_order(client)

    toxiproxy.post(PROXY, json={"enabled": False})
    try:
        response = client.post(f"/api/v1/orders/{order['id']}/accept", timeout=15.0)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    finally:
        toxiproxy.post(PROXY, json={"enabled": True})

    # The transition did not take effect.
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if client.get("/health/ready").status_code == 200:
            break
        time.sleep(0.5)
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "PLACED"


# --------------------------------------------------------------------------
# ASR-A4 - Atomic payment verification
# --------------------------------------------------------------------------


def test_asra4_transaction_rollback_leaves_no_partial_state(client: httpx.Client) -> None:
    """A fault mid-transaction rolls back all three updates as one unit."""
    order, invoice, payment = advance_to_paid(client)
    client.post("/internal/test/reset")

    before = metrics(client)
    faulted = client.post(
        f"/api/v1/payments/{payment['id']}/verify",
        headers={"X-Test-Fault": "after-payment-update"},
    )
    assert faulted.status_code in (500, 503), faulted.text
    assert faulted.json()["error"]["code"] == "TRANSACTION_FAILED"

    after = metrics(client)
    assert after["transaction_rollbacks_total"] > before["transaction_rollbacks_total"]

    # The rollback restores exactly the end-of-step-4 state. Order PAID with
    # Payment PENDING is correct, not an inconsistency.
    assert client.get(f"/api/v1/payments/{payment['id']}").json()["status"] == "PENDING"
    assert client.get(f"/api/v1/invoices/{invoice['id']}").json()["status"] == "ISSUED"
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "PAID"

    # A subsequent verification without the fault succeeds.
    clean = client.post(f"/api/v1/payments/{payment['id']}/verify")
    assert clean.status_code == 200

    assert client.get(f"/api/v1/payments/{payment['id']}").json()["status"] == "VERIFIED"
    assert client.get(f"/api/v1/invoices/{invoice['id']}").json()["status"] == "PAID"
    assert client.get(f"/api/v1/orders/{order['id']}").json()["status"] == "VERIFIED"


def test_asra4_invoice_creation_is_atomic(client: httpx.Client) -> None:
    """Invoice creation updates both Invoice and Order, or neither."""
    from tests.conftest import make_order

    _, _, order = make_order(client)
    client.post(f"/api/v1/orders/{order['id']}/accept")

    invoice = client.post("/api/v1/invoices", json={"orderRef": order["id"]})
    assert invoice.status_code == 201

    # Both records advanced together.
    order_body = client.get(f"/api/v1/orders/{order['id']}").json()
    assert order_body["status"] == "INVOICED"
    assert order_body["invoiceRef"] == invoice.json()["id"]


# --------------------------------------------------------------------------
# Test-hook contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header_value",
    ["nonsense", "transient-db-failures=abc", "transient-db-failures=-1", ""],
)
def test_malformed_test_fault_header_is_ignored_silently(
    client: httpx.Client, header_value: str
) -> None:
    """A bad test header never turns into a 400; the request proceeds normally."""
    product = make_product(client, amount="7.77")
    response = client.get(
        f"/api/v1/products/{product['id']}", headers={"X-Test-Fault": header_value}
    )
    assert response.status_code == 200


@pytest.mark.parametrize("header_value", ["abc", "-5", "99999999"])
def test_malformed_delay_header_is_ignored_silently(
    client: httpx.Client, header_value: str
) -> None:
    product = make_product(client, amount="7.77")
    response = client.get(
        f"/api/v1/products/{product['id']}", headers={"X-Test-Delay-Ms": header_value}
    )
    assert response.status_code == 200


def test_reset_endpoint_clears_counters_and_cache(client: httpx.Client) -> None:
    product = make_product(client, amount="7.77")
    client.get(f"/api/v1/products/{product['id']}")
    assert sum(metrics(client).values()) > 0

    assert client.post("/internal/test/reset").status_code == 204
    counters = metrics(client)
    # Counters are zeroed; the metrics GET itself bypasses admission control and
    # therefore does not re-increment requests_accepted_total.
    assert counters["cache_hits_total"] == 0
    assert counters["cache_misses_total"] == 0
    assert counters["db_product_reads_total"] == 0
    assert counters["requests_accepted_total"] == 0
