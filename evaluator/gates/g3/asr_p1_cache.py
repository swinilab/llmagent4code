"""ASR-P1 -- Performance > Manage Resources > Maintain Multiple Copies of Data.

Two questions, deliberately separated.

The staleness probe asks whether a maintained copy exists at all. A product row
is changed directly in PostgreSQL, behind the application's back, so it has no
opportunity to invalidate anything. Serving the old value afterwards proves a
copy is being kept; serving the new value once the TTL has passed proves the
copy expires. This is black-box evidence that no counter can fake -- it is
stronger than cache_hits_total, which an application could simply invent.

The throughput probe then asks whether the copy is actually load-bearing: a
thousand reads should reach the database only a handful of times. The
database-side scan delta is the authoritative number here; the application's own
counter is recorded beside it and must agree.

A third probe isolates a single refill, because the first two cannot tell a
single-flight cache from one without it. Across a thousand reads the few TTL
refills are lost in the budget whichever way they are served -- a calibration
run with single-flight deliberately disabled still passed comfortably. Timing
the expiry and hitting it with every reader at once makes the difference plain:
one read if the refill is shared, one per reader if it is not.
"""

from __future__ import annotations

import time
from typing import Any

from ...harness import trace
from ...harness.appmetrics import MetricsContractError
from ...harness.context import Context, SeedError
from ...harness.pgprobe import SchemaDiscoveryError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-P1"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_p1"]
    ttl = int(ctx.thresholds["app_config"]["CACHE_TTL_SECONDS"])
    started = time.monotonic()

    try:
        with trace.step("seed", f"one product described {cfg['pre_expiry_description']!r}"):
            ctx.reset()
            product_id = ctx.seed_product(description=cfg["pre_expiry_description"])
            table = ctx.product_table()
            trace.note(f"product={product_id} table={table} ttl={ttl}s")
    except (SeedError, SchemaDiscoveryError, MetricsContractError) as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    assertions: list[Assertion] = []
    observations: dict[str, Any] = {}

    # ── staleness probe ───────────────────────────────────────────────────
    with trace.step("warm the cache", "expect 200"):
        warm = ctx.http.get(f"/api/v1/products/{product_id}")
        trace.response_line("warming read", warm, expected=200)
    if warm.status != 200:
        return ScenarioRun.not_exercisable(
            ctx.app_id, SCENARIO_ID, run_index,
            f"warming read returned HTTP {warm.status}",
        )

    try:
        with trace.step(
            "mutate the row behind the application",
            f"UPDATE {table} SET description = {cfg['post_expiry_description']!r}",
        ):
            ctx.pg.set_product_description(table, product_id, cfg["post_expiry_description"])
    except SchemaDiscoveryError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    with trace.step(
        "pre-expiry read",
        f"expect the cached {cfg['pre_expiry_description']!r}, not the new row value",
    ):
        pre_expiry = _description(ctx.http.get(f"/api/v1/products/{product_id}"))
        trace.note(f"description={pre_expiry!r}")
    assertions.append(
        assert_that(
            "pre-expiry read serves the maintained copy",
            pre_expiry == cfg["pre_expiry_description"],
            cfg["pre_expiry_description"],
            pre_expiry,
            note="the row was changed directly in PostgreSQL; serving the old value proves a copy exists",
        )
    )

    with trace.step(
        "post-expiry read",
        f"after waiting {ttl + 1}s, expect PostgreSQL's "
        f"{cfg['post_expiry_description']!r}",
    ):
        time.sleep(ttl + 1)
        post_expiry = _description(ctx.http.get(f"/api/v1/products/{product_id}"))
        trace.note(f"description={post_expiry!r}")
    assertions.append(
        assert_that(
            "post-expiry read reflects PostgreSQL",
            post_expiry == cfg["post_expiry_description"],
            cfg["post_expiry_description"],
            post_expiry,
            note="the copy must expire; PostgreSQL remains authoritative",
        )
    )
    observations["pre_expiry_description"] = pre_expiry
    observations["post_expiry_description"] = post_expiry

    # ── throughput probe ──────────────────────────────────────────────────
    try:
        ctx.reset()
        ctx.http.get(f"/api/v1/products/{product_id}")   # single warming read
        before = ctx.metrics.read()
    except MetricsContractError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    scans_before = ctx.pg.scan_counts(table)
    with trace.step(
        "throughput probe",
        f"{cfg['measured_reads']} reads at concurrency {cfg['concurrency']}; expect "
        f"p95 <= {cfg['p95_ms_max']}ms, <= {cfg['db_product_reads_max']} db reads",
    ):
        workload = ctx.http.run_concurrent(
            "GET",
            f"/api/v1/products/{product_id}",
            total=cfg["measured_reads"],
            concurrency=cfg["concurrency"],
        )
        ctx.pg.wait_for_stats()
        scan_delta = ctx.pg.scan_counts(table).delta(scans_before)
        after = ctx.metrics.read()
        delta = after.delta(before)

        hit_rate = _hit_rate(delta)
        p95 = workload.p95_ms()
        error_rate = workload.error_rate()
        trace.summarise_workload(
            "reads", workload,
            extra={"pg_scan_delta": scan_delta, "cache_hit_rate": round(hit_rate, 4)},
        )
        trace.note(f"pg scan delta={scan_delta} hit_rate={hit_rate:.1%}")

    assertions += [
        assert_that(
            "database reads stay within budget",
            scan_delta <= cfg["db_product_reads_max"],
            f"<= {cfg['db_product_reads_max']}",
            scan_delta,
            note="pg_stat scan delta -- the authoritative count, independent of the application",
        ),
        assert_that(
            "reported reads agree with the database",
            _agrees(delta["db_product_reads_total"], scan_delta),
            f"~{scan_delta}",
            delta["db_product_reads_total"],
            evidence=Evidence.APP_REPORTED,
            note="a large divergence indicates fabricated counters",
        ),
        assert_that(
            "cache hit rate",
            hit_rate >= cfg["cache_hit_rate_min"],
            f">= {cfg['cache_hit_rate_min']:.0%}",
            f"{hit_rate:.1%}",
            evidence=Evidence.APP_REPORTED,
        ),
        assert_that(
            "p95 response time",
            p95 <= cfg["p95_ms_max"],
            f"<= {cfg['p95_ms_max']} ms",
            f"{p95:.0f} ms",
        ),
        assert_that(
            "error rate",
            error_rate <= cfg["error_rate_max"],
            f"<= {cfg['error_rate_max']:.0%}",
            f"{error_rate:.1%}",
        ),
    ]

    # ── single-flight probe ───────────────────────────────────────────────
    # The throughput phase above cannot distinguish a single-flight cache from
    # one without it: over a thousand reads the handful of TTL refills are lost
    # in the budget either way. This phase isolates one refill and asks how many
    # database reads it costs.
    refill_reads = _measure_refill_cost(ctx, product_id, ttl, cfg["concurrency"])
    assertions.append(
        assert_that(
            "a concurrent refill costs one database read",
            refill_reads <= _SINGLE_FLIGHT_TOLERANCE,
            f"<= {_SINGLE_FLIGHT_TOLERANCE}",
            refill_reads,
            evidence=Evidence.APP_REPORTED,
            note="every reader arrives at an expired entry simultaneously; without "
            "single-flight each issues its own read, so the count tracks concurrency",
        )
    )

    observations.update(
        {
            "db_reads_pg": scan_delta,
            "db_reads_reported": delta["db_product_reads_total"],
            "cache_hit_rate": round(hit_rate, 4),
            "p95_ms": round(p95, 1),
            "error_rate": round(error_rate, 4),
            "status_distribution": workload.status_distribution(),
            "reads_per_concurrent_refill": refill_reads,
        }
    )

    return ScenarioRun.from_assertions(
        ctx.app_id, SCENARIO_ID, run_index, assertions, observations,
        duration_s=time.monotonic() - started,
        logs_excerpt=_logs_if_failed(ctx, assertions),
    )


# One read for the refill itself. The allowance above it absorbs a reader that
# arrives a moment late and legitimately misses the just-stored entry; it does
# not absorb a cache where every concurrent miss loads independently, which
# costs as many reads as there are readers.
_SINGLE_FLIGHT_TOLERANCE = 3


def _measure_refill_cost(ctx: Context, product_id: str, ttl: int, concurrency: int) -> int:
    """Count the database reads caused by one simultaneous refill.

    The entry is warmed, then left to expire, then hit by every reader at once.
    A single-flight cache loads once and serves the rest from that load; one
    without it issues a read per reader. Isolating a single refill is what makes
    the difference visible -- across a long throughput run it is not.

    Counted from the application's own read counter rather than pg_stat, since
    a primary-key lookup registers as no scan at all. The counter is credible
    here because the throughput phase has already cross-checked it against the
    database, and because inflating it would only make this assertion harder to
    pass.
    """
    import time as _time

    ctx.reset()
    ctx.http.get(f"/api/v1/products/{product_id}")   # warm
    _time.sleep(ttl + 1)                              # let it expire

    before = ctx.metrics.read()
    ctx.http.run_simultaneous(
        "GET", f"/api/v1/products/{product_id}", total=concurrency, timeout_s=30.0
    )
    return ctx.metrics.read().delta(before)["db_product_reads_total"]


def _description(resp: Any) -> str | None:
    return resp.body.get("description") if isinstance(resp.body, dict) else None


def _hit_rate(delta: dict[str, int]) -> float:
    hits = delta.get("cache_hits_total", 0)
    total = hits + delta.get("cache_misses_total", 0)
    return hits / total if total else 0.0


def _agrees(reported: int, observed: int, tolerance: int = 10) -> bool:
    """Allow a small divergence between the two read counts.

    They measure subtly different things -- the application counts statements it
    issued, PostgreSQL counts scans those statements performed -- so an exact
    match is not required. A gap far beyond this band means the reported figure
    is not describing the same activity.
    """
    return abs(reported - observed) <= max(tolerance, observed // 2)


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=200)
    except Exception:
        return ""
