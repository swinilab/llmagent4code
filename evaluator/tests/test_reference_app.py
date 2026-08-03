"""Checks on the reference application's tactic mechanisms.

The reference application is the instrument used to calibrate the evaluator, so
it has to be right before it can certify anything. These tests exercise the two
mechanisms whose correctness is least obvious by inspection -- the single-flight
cache and the immediate-rejection semaphore -- without needing Docker or a
database, by driving them directly.

The full six-scenario calibration still requires the container stack; this is
the fast check that catches an outright mistake before spending minutes on a
deployment.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluator" / "reference_app"))

from app.admission import AdmissionController          # noqa: E402
from app.cache import DependencyUnavailable, ProductCache  # noqa: E402
from app.observability import Metrics                  # noqa: E402


# ── single-flight cache ───────────────────────────────────────────────────


def test_concurrent_misses_produce_one_load() -> None:
    """Fifty simultaneous readers of a cold key must load it once.

    Without this, the first refill costs fifty database reads and ASR-P1's
    budget is gone before the measurement starts. This is the single most
    load-bearing detail in the cache.
    """
    cache = ProductCache(ttl_seconds=5)
    loads = []
    lock = threading.Lock()

    def loader():
        with lock:
            loads.append(1)
        time.sleep(0.05)   # widen the window a naive cache would race through
        return {"id": "p1"}

    barrier = threading.Barrier(50)

    def reader():
        barrier.wait()
        cache.get("p1", loader)

    threads = [threading.Thread(target=reader) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(loads) == 1, f"expected one load, got {len(loads)}"


def test_entry_expires_so_the_database_stays_authoritative() -> None:
    """ASR-P1 requires a post-TTL read to reflect a direct database change."""
    cache = ProductCache(ttl_seconds=1)
    version = {"v": "A"}
    cache.get("p1", lambda: dict(version))
    version["v"] = "B"

    assert cache.get("p1", lambda: dict(version))["v"] == "A", "should still serve the copy"
    time.sleep(1.1)
    assert cache.get("p1", lambda: dict(version))["v"] == "B", "should refresh after the TTL"


def test_stale_copy_survives_an_unreachable_database() -> None:
    """ASR-A3: past its TTL, an entry is still served when the database is gone.

    The TTL and the degraded horizon are separate lifetimes precisely so this
    can hold without breaking the expiry test above.
    """
    cache = ProductCache(ttl_seconds=1)
    cache.get("p1", lambda: {"v": "warmed"})
    time.sleep(1.1)

    def unreachable():
        raise DependencyUnavailable("proxy disabled")

    assert cache.get("p1", unreachable)["v"] == "warmed"


def test_nothing_is_invented_for_an_unwarmed_key() -> None:
    """An unwarmed read during an outage must fail, not fabricate.

    Serving something here would look like graceful degradation while actually
    being made-up data, which the specification rules out explicitly.
    """
    cache = ProductCache(ttl_seconds=5)

    def unreachable():
        raise DependencyUnavailable("proxy disabled")

    try:
        cache.get("never-loaded", unreachable)
    except DependencyUnavailable:
        return
    raise AssertionError("an unwarmed key must not be served during an outage")


def test_different_keys_do_not_block_each_other() -> None:
    """Per-key locking: a slow refill of one product must not stall another."""
    cache = ProductCache(ttl_seconds=5)
    started = threading.Event()

    def slow():
        started.set()
        time.sleep(0.4)
        return {"id": "slow"}

    t = threading.Thread(target=lambda: cache.get("slow-key", slow))
    t.start()
    started.wait(timeout=1.0)

    begun = time.perf_counter()
    cache.get("fast-key", lambda: {"id": "fast"})
    elapsed = time.perf_counter() - begun
    t.join()

    assert elapsed < 0.2, f"unrelated key blocked for {elapsed:.2f}s"


# ── admission control ─────────────────────────────────────────────────────


def test_admission_refuses_beyond_the_limit() -> None:
    controller = AdmissionController(limit=10)
    admitted = [controller.try_acquire() for _ in range(15)]
    assert sum(admitted) == 10
    assert admitted[:10] == [True] * 10
    assert admitted[10:] == [False] * 5


def test_refusal_is_immediate() -> None:
    """The property that distinguishes limiting from queueing.

    A bounded queue also ends up rejecting, just later; ASR-P2's rejection
    latency measure is the only thing that separates the two, so the refusal
    path must not wait.
    """
    controller = AdmissionController(limit=1)
    assert controller.try_acquire()

    begun = time.perf_counter()
    assert not controller.try_acquire()
    elapsed_ms = (time.perf_counter() - begun) * 1000
    assert elapsed_ms < 5, f"refusal took {elapsed_ms:.1f}ms; it must not wait for a slot"


def test_delay_hook_does_not_block_the_event_loop() -> None:
    """The injected delay must yield, not stall the whole server.

    A synchronous sleep inside the middleware blocks the event loop, so no other
    request can be picked up while it runs -- including the ones admission
    control exists to refuse instantly. Rejections then arrive seconds late and
    the scenario reports queueing behaviour from a semaphore that is perfectly
    correct. A live overload run is what exposed this; the source is checked
    here because reproducing it needs two hundred concurrent connections.
    """
    import ast
    import inspect
    import textwrap

    from app.admission import AdmissionController, TestHookMiddleware

    # Parsed rather than string-matched: the comment explaining this hazard
    # names time.sleep, and a substring check would flag the explanation.
    tree = ast.parse(textwrap.dedent(inspect.getsource(TestHookMiddleware.dispatch)))
    calls = {
        f"{getattr(n.func.value, 'id', '')}.{n.func.attr}"
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert "asyncio.sleep" in calls
    assert "time.sleep" not in calls

    # The deliberate-defect path must model queueing, not a stalled loop.
    assert inspect.iscoroutinefunction(AdmissionController.acquire_blocking)


def test_slots_are_returned_on_release() -> None:
    controller = AdmissionController(limit=2)
    controller.try_acquire()
    controller.try_acquire()
    assert not controller.try_acquire()
    controller.release()
    assert controller.try_acquire()


def test_admission_counting_is_thread_safe() -> None:
    """Under contention the limit must hold exactly, not approximately."""
    controller = AdmissionController(limit=10)
    results: list[bool] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(100)

    def contend():
        barrier.wait()
        got = controller.try_acquire()
        with results_lock:
            results.append(got)

    threads = [threading.Thread(target=contend) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(results) == 10, f"admitted {sum(results)}, expected exactly 10"


# ── metrics ───────────────────────────────────────────────────────────────


def test_metrics_are_monotonic_and_resettable() -> None:
    m = Metrics()
    m.increment("cache_hits_total")
    m.increment("cache_hits_total", by=4)
    assert m.snapshot()["cache_hits_total"] == 5
    m.reset()
    assert m.snapshot()["cache_hits_total"] == 0


def test_metric_increments_survive_concurrency() -> None:
    """A lost update here would make the reported counts disagree with reality."""
    m = Metrics()
    threads = [
        threading.Thread(target=lambda: [m.increment("cache_hits_total") for _ in range(200)])
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.snapshot()["cache_hits_total"] == 2000
