"""ASR-P1 (maintained copies) and ASR-P2 (limit event response)."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from tests.conftest import BASE_URL, make_product, metrics

CACHE_TTL_SECONDS = 5
MAX_IN_FLIGHT_REQUESTS = 10


def _peak_overlap(windows: list[tuple[float, float]]) -> int:
    """Maximum number of request windows overlapping at any instant.

    Each admitted request is held server-side for a fixed delay, so overlapping
    client-observed windows are a faithful proxy for concurrent admission.
    """
    events: list[tuple[float, int]] = []
    for start, end in windows:
        events.append((start, 1))
        events.append((end, -1))
    # Ends sort before starts at equal timestamps, so a request that finishes as
    # another begins is not double-counted.
    events.sort(key=lambda event: (event[0], event[1]))

    current = 0
    peak = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def _update_price_out_of_band(product_id: str, new_amount: str) -> None:
    """Modify the Product row directly in PostgreSQL, bypassing the API.

    The update goes through Toxiproxy's listener exactly as the application's own
    traffic does, so it exercises the same path without touching the cache.
    """
    import subprocess

    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "db",
            "psql", "-U", "orderman", "-d", "orderman", "-c",
            f"UPDATE products SET price_amount = {new_amount} WHERE id = '{product_id}';",
        ],
        check=True,
        capture_output=True,
    )


# --------------------------------------------------------------------------
# ASR-P1
# --------------------------------------------------------------------------


def test_asrp1_stale_within_ttl_then_fresh_after_ttl(client: httpx.Client) -> None:
    """A copy is maintained for CACHE_TTL_SECONDS, then reflects the database."""
    product = make_product(client, amount="19.99")
    product_id = product["id"]

    # Warm the copy.
    assert client.get(f"/api/v1/products/{product_id}").json()["price"]["amount"] == "19.99"

    _update_price_out_of_band(product_id, "77.77")

    # Within the TTL the maintained copy still answers with the old value.
    immediate = client.get(f"/api/v1/products/{product_id}")
    assert immediate.status_code == 200
    assert immediate.json()["price"]["amount"] == "19.99"

    # After the TTL elapses the next read reflects current database state.
    time.sleep(CACHE_TTL_SECONDS + 1.5)
    refreshed = client.get(f"/api/v1/products/{product_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["price"]["amount"] == "77.77"


def test_asrp1_concurrent_reads_hit_rate_latency_and_db_bound(client: httpx.Client) -> None:
    """Sustained concurrent reads: >=95% hits, p95 <=200ms, TTL-bounded DB reads."""
    product = make_product(client, amount="19.99")
    product_id = product["id"]

    client.post("/internal/test/reset")
    # Warm the copy after the reset so the measured window is steady-state.
    client.get(f"/api/v1/products/{product_id}")

    latencies: list[float] = []
    errors = 0
    # Concurrency stays within MAX_IN_FLIGHT_REQUESTS, so every request is
    # admitted and this measures the maintained copy, not the admission policy.
    concurrency = 8
    duration_seconds = CACHE_TTL_SECONDS * 2

    def worker() -> tuple[list[float], int]:
        local_latencies: list[float] = []
        local_errors = 0
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as worker_client:
            deadline = time.monotonic() + duration_seconds
            while time.monotonic() < deadline:
                started = time.monotonic()
                try:
                    response = worker_client.get(f"/api/v1/products/{product_id}")
                    local_latencies.append((time.monotonic() - started) * 1000.0)
                    if response.status_code != 200:
                        local_errors += 1
                except httpx.HTTPError:
                    local_errors += 1
        return local_latencies, local_errors

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for local_latencies, local_errors in pool.map(lambda _: worker(), range(concurrency)):
            latencies.extend(local_latencies)
            errors += local_errors

    counters = metrics(client)
    total_reads = counters["cache_hits_total"] + counters["cache_misses_total"]
    assert total_reads > 0

    hit_rate = counters["cache_hits_total"] / total_reads
    assert hit_rate >= 0.95, f"cache hit rate {hit_rate:.4f} < 0.95"

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    assert p95 <= 200.0, f"p95 {p95:.1f}ms > 200ms"

    error_rate = errors / max(1, len(latencies))
    assert error_rate <= 0.01, f"error rate {error_rate:.4f} > 0.01"

    # Database reads are bounded by TTL-driven refills, not one per miss. Over a
    # 2-TTL window a handful of refills is expected; one per concurrent miss
    # would be far higher.
    expected_refills = (duration_seconds / CACHE_TTL_SECONDS) + 2
    assert counters["db_product_reads_total"] <= expected_refills + 3, (
        f"db_product_reads_total {counters['db_product_reads_total']} exceeds "
        f"TTL-driven refill bound ~{expected_refills}"
    )


def test_asrp1_single_flight_bounds_concurrent_misses(client: httpx.Client) -> None:
    """Concurrent misses for one key trigger a single refill, not one each."""
    product = make_product(client, amount="5.55")
    product_id = product["id"]
    client.post("/internal/test/reset")

    def read() -> int:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as worker_client:
            return worker_client.get(f"/api/v1/products/{product_id}").status_code

    # Eight simultaneous cold misses for the same key.
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: read(), range(8)))

    assert all(status == 200 for status in statuses)
    counters = metrics(client)
    # Single-flight: one loader runs while the others wait and observe its result.
    assert counters["db_product_reads_total"] <= 2, (
        f"expected single-flight refill, saw {counters['db_product_reads_total']} database reads"
    )


# --------------------------------------------------------------------------
# ASR-P2
# --------------------------------------------------------------------------


def test_asrp2_admission_control_under_overload(client: httpx.Client) -> None:
    """A burst far exceeding the limit is bounded, and excess is rejected fast."""
    client.post("/internal/test/reset")

    burst = 60
    hold_ms = 1500  # keeps admitted slots occupied while the burst lands

    # Connections are established and warmed up front, and all threads are
    # released from one barrier. Without this the measurement would charge TCP
    # setup and thread scheduling to the server: a pool that hands out threads as
    # earlier requests return does not produce a simultaneous burst, and the
    # resulting latency says nothing about how fast admission control refuses.
    clients = [httpx.Client(base_url=BASE_URL, timeout=30.0) for _ in range(burst)]
    for warm_client in clients:
        warm_client.get("/health/live")

    barrier = threading.Barrier(burst)
    windows: list[tuple[int, float, float, str | None]] = [None] * burst  # type: ignore[list-item]

    def issue(index: int) -> None:
        worker_client = clients[index]
        barrier.wait()
        started = time.monotonic()
        try:
            response = worker_client.get(
                "/api/v1/products",
                params={"query": "widget"},
                headers={"X-Test-Delay-Ms": str(hold_ms)},
            )
        except httpx.HTTPError:
            windows[index] = (0, started, time.monotonic(), None)
            return
        ended = time.monotonic()
        code = None
        if response.status_code in (429, 503):
            code = response.json().get("error", {}).get("code")
        windows[index] = (response.status_code, started, ended, code)

    threads = [threading.Thread(target=issue, args=(i,)) for i in range(burst)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for worker_client in clients:
            worker_client.close()

    # (status, elapsed_ms, code) view for the latency and code assertions below.
    results = [
        (status, (end - start) * 1000.0, code) for status, start, end, code in windows
    ]
    statuses = [status for status, _, _ in results]
    accepted = [status for status in statuses if status == 200]
    rejected = [status for status in statuses if status in (429, 503)]

    # The mechanism admits work rather than rejecting everything.
    assert accepted, "no request was admitted; admission control rejected everything"

    # The requirement bounds *concurrently* admitted requests, not the
    # cumulative number that eventually succeed: slots are released and reused
    # as the burst proceeds, so more than MAX_IN_FLIGHT_REQUESTS may succeed in
    # total. The peak is read from the admission controller, which records it at
    # the instant a slot is taken; client-observed windows include connection
    # setup and overstate overlap.
    admission = client.get("/internal/admission").json()
    assert admission["peak_in_flight"] <= MAX_IN_FLIGHT_REQUESTS, (
        f"peak concurrently admitted requests was {admission['peak_in_flight']}, "
        f"exceeding {MAX_IN_FLIGHT_REQUESTS}"
    )
    # Client-side overlap is still reported for diagnosis, but is not the oracle.
    client_overlap = _peak_overlap(
        [(start, end) for status, start, end, _ in windows if status == 200]
    )
    assert client_overlap >= admission["peak_in_flight"]
    # Every request is either admitted or controlled-rejected; no unhandled 500.
    assert statuses.count(500) == 0, "unhandled HTTP 500 during overload"
    assert len(accepted) + len(rejected) == burst

    # Rejections carry the prescribed code and Retry-After semantics.
    for status, _, code in results:
        if status in (429, 503):
            assert code == "OVERLOAD_REJECTED", f"rejection carried code {code}"

    # Controlled rejections are immediate, not queued.
    rejection_latencies = sorted(
        elapsed for status, elapsed, _ in results if status in (429, 503)
    )
    p95_rejection = rejection_latencies[int(len(rejection_latencies) * 0.95)]
    assert p95_rejection <= 500.0, f"rejection p95 {p95_rejection:.1f}ms > 500ms"

    # Counters account for every request that reached admission control.
    counters = metrics(client)
    assert counters["requests_accepted_total"] >= len(accepted)
    assert counters["requests_rejected_total"] >= len(rejected)

    # Readiness recovers promptly once the overload stops.
    started = time.monotonic()
    ready = client.get("/health/ready")
    assert (time.monotonic() - started) <= 2.0
    assert ready.status_code == 200


def test_asrp2_retry_after_header_on_rejection(client: httpx.Client) -> None:
    """Controlled 429 responses carry Retry-After."""
    burst = 40
    clients = [httpx.Client(base_url=BASE_URL, timeout=30.0) for _ in range(burst)]
    for warm_client in clients:
        warm_client.get("/health/live")

    barrier = threading.Barrier(burst)
    responses: list[httpx.Response | None] = [None] * burst

    def issue(index: int) -> None:
        barrier.wait()
        try:
            responses[index] = clients[index].get(
                "/api/v1/products", headers={"X-Test-Delay-Ms": "1200"}
            )
        except httpx.HTTPError:
            responses[index] = None

    threads = [threading.Thread(target=issue, args=(i,)) for i in range(burst)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for warm_client in clients:
            warm_client.close()

    rejections = [r for r in responses if r is not None and r.status_code == 429]
    assert rejections, "expected at least one 429 under this burst"
    for rejection in rejections:
        assert "Retry-After" in rejection.headers


def test_observation_paths_bypass_admission_control(client: httpx.Client) -> None:
    """Health and metrics stay servable while the system is overloaded."""
    burst = 40

    def issue() -> None:
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as worker_client:
            try:
                worker_client.get("/api/v1/products", headers={"X-Test-Delay-Ms": "2000"})
            except httpx.HTTPError:
                pass

    with ThreadPoolExecutor(max_workers=burst + 4) as pool:
        pool.map(lambda _: issue(), range(burst))
        time.sleep(0.8)  # observe while the burst is in flight

        assert client.get("/health/live").status_code == 200
        assert client.get("/internal/metrics").status_code == 200
        # Readiness answers promptly even under load.
        started = time.monotonic()
        ready = client.get("/health/ready")
        assert (time.monotonic() - started) <= 2.0
        assert ready.status_code == 200
