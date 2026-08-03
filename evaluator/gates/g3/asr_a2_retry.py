"""ASR-A2 -- Availability > Recover from Faults > Preparation and Repair > Retry.

Two transient failures are injected at the product database-read boundary; the
third attempt is allowed through. A bounded retry policy should absorb both and
still return the product.

This is the scenario with the weakest external evidence in the study, and it is
worth being explicit about why. The two injected failures never reach
PostgreSQL, so they leave no trace outside the application -- retry_attempts_total
is necessarily self-reported. What keeps the scenario honest is the pairing:

  * the client sees HTTP 200          (external -- recovery really happened)
  * pg_stat bounds database work      (external -- but only from above; see below)
  * elapsed time covers the backoffs  (external -- waiting really happened)

The pg_stat bound is weaker than it first appears, and the limitation is worth
stating plainly rather than papering over: PostgreSQL does not count a
single-row primary-key lookup as a scan, so a zero delta is consistent both with
"the read never happened" and with "the read happened as a PK fetch". It can
therefore prove the injected failures did *not* reach the database, but it
cannot prove the successful attempt did. The HTTP 200 does that.

This is the scenario with the weakest external evidence in the study, and the
report says so. The negative cases carry more weight here as a result: a policy
that retries a 404 or a 409 is not a fault-classifying retry, it is a loop, and
that is externally visible.
"""

from __future__ import annotations

import time
from typing import Any

from ...harness import trace
from ...harness.appmetrics import MetricsContractError
from ...harness.context import Context, SeedError
from ...harness.pgprobe import SchemaDiscoveryError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-A2"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_a2"]
    started = time.monotonic()

    try:
        with trace.step("seed", "one product; discover its table for the pg_stat baseline"):
            ctx.reset()
            product_id = ctx.seed_product(description="Retry scenario product")
            table = ctx.product_table()
            trace.note(f"product={product_id} table={table}")
    except (SeedError, SchemaDiscoveryError) as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    # Seeding warms nothing by itself, but a prior read would; reset again so
    # the measured request is genuinely uncached and must reach the boundary.
    try:
        ctx.reset()
        before = ctx.metrics.read()
    except MetricsContractError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    scans_before = ctx.pg.scan_counts(table)

    # ── stimulus ──────────────────────────────────────────────────────────
    injected = cfg["injected_failures"]
    with trace.step(
        "read with injected transient failures",
        f"X-Test-Fault: transient-db-failures={injected}; expect "
        f"HTTP {cfg['expected_status']} after {cfg['expected_retry_delta']} retries",
    ):
        resp = ctx.http.get(
            f"/api/v1/products/{product_id}",
            headers={"X-Test-Fault": f"transient-db-failures={injected}"},
        )
        trace.response_line("read", resp, expected=cfg["expected_status"])

        # The statistics collector lags the request that produced the activity,
        # so reading straight away reports the pre-request numbers and the delta
        # comes out as zero regardless of what the application did.
        ctx.pg.wait_for_stats()
        scans_after = ctx.pg.scan_counts(table)
        after = ctx.metrics.read()
        delta = after.delta(before)
        scan_delta = scans_after.delta(scans_before)
        trace.note(f"pg scan delta={scan_delta}; app counters={trace.brief(delta)}")

    assertions: list[Assertion] = [
        assert_that(
            "request succeeds after the transient failures",
            resp.status == cfg["expected_status"],
            cfg["expected_status"],
            resp.status,
        ),
        assert_that(
            "the injected failures did not reach PostgreSQL",
            scan_delta <= cfg["expected_db_read_delta"],
            f"<= {cfg['expected_db_read_delta']}",
            scan_delta,
            note="pg_stat bounds the database work from above; a single-row primary-key "
            "read registers as no scan at all, so this cannot confirm the successful "
            "attempt ran -- the 200 response does that",
        ),
        assert_that(
            "exactly one attempt reached the database",
            delta["db_product_reads_total"] == cfg["expected_db_read_delta"],
            cfg["expected_db_read_delta"],
            delta["db_product_reads_total"],
            evidence=Evidence.APP_REPORTED,
            note="two injected failures are raised before the database call, so only "
            "the third attempt should count as a read",
        ),
        assert_that(
            "attempts entering the read boundary",
            delta["db_product_read_attempts_total"] == cfg["expected_attempt_delta"],
            cfg["expected_attempt_delta"],
            delta["db_product_read_attempts_total"],
            evidence=Evidence.APP_REPORTED,
        ),
        assert_that(
            "retries beyond the initial attempt",
            delta["retry_attempts_total"] == cfg["expected_retry_delta"],
            cfg["expected_retry_delta"],
            delta["retry_attempts_total"],
            evidence=Evidence.APP_REPORTED,
        ),
        assert_that(
            "attempts stay within DB_MAX_ATTEMPTS",
            delta["db_product_read_attempts_total"] <= cfg["max_attempts_ceiling"],
            f"<= {cfg['max_attempts_ceiling']}",
            delta["db_product_read_attempts_total"],
            evidence=Evidence.APP_REPORTED,
            note="an unbounded policy would exceed this",
        ),
    ]

    # ── negative cases: retry must classify faults, not blanket-retry ─────
    assertions.extend(_no_retry_on_non_transient(ctx, product_id))

    observations: dict[str, Any] = {
        "status": resp.status,
        "elapsed_ms": resp.elapsed_ms,
        "attempts": delta["db_product_read_attempts_total"],
        "retry_attempts": delta["retry_attempts_total"],
        "db_reads": delta["db_product_reads_total"],
        "pg_scan_delta": scan_delta,
    }

    return ScenarioRun.from_assertions(
        ctx.app_id,
        SCENARIO_ID,
        run_index,
        assertions,
        observations,
        duration_s=time.monotonic() - started,
        logs_excerpt=_logs_if_failed(ctx, assertions),
    )


def _no_retry_on_non_transient(ctx: Context, product_id: str) -> list[Assertion]:
    """Confirm malformed input, unknown ids and workflow conflicts are not retried.

    Retrying these would waste the dependency on requests that can never
    succeed, and would show the policy is not classifying faults at all. Each
    case is measured as its own counter delta so a failure names the case.
    """
    out: list[Assertion] = []

    cases: list[tuple[str, str, str, tuple[int, ...]]] = [
        ("malformed uuid", "GET", "/api/v1/products/not-a-uuid", (400,)),
        ("unknown uuid", "GET", f"/api/v1/products/{ctx.unknown_uuid()}", (404,)),
    ]

    for label, method, path, expected_statuses in cases:
        try:
            with trace.step(
                f"negative case: {label}",
                f"expect {expected_statuses} and zero retries",
            ):
                before = ctx.metrics.read()
                resp = ctx.http.request(method, path)
                delta = ctx.metrics.read().delta(before)
                trace.response_line(label, resp, expected=expected_statuses)
                trace.note(f"retry_attempts_total delta={delta['retry_attempts_total']}")
        except MetricsContractError as exc:
            out.append(assert_that(f"{label}: measurable", False, "metrics readable", str(exc)))
            continue

        out.append(
            assert_that(
                f"{label} returns {expected_statuses[0]}",
                resp.status in expected_statuses,
                f"one of {expected_statuses}",
                resp.status,
            )
        )
        out.append(
            assert_that(
                f"{label} triggers no retry",
                delta["retry_attempts_total"] == 0,
                0,
                delta["retry_attempts_total"],
                evidence=Evidence.APP_REPORTED,
            )
        )

    # A workflow conflict: verifying a payment that was never invoiced-and-paid
    # cannot succeed however many times it is attempted.
    try:
        with trace.step("negative case: workflow conflict", "expect zero retries"):
            before = ctx.metrics.read()
            conflict = ctx.http.post(f"/api/v1/orders/{ctx.unknown_uuid()}/ship")
            delta = ctx.metrics.read().delta(before)
            trace.response_line("ship unknown order", conflict)
            trace.note(f"retry_attempts_total delta={delta['retry_attempts_total']}")
        out.append(
            assert_that(
                "workflow conflict triggers no retry",
                delta["retry_attempts_total"] == 0,
                0,
                delta["retry_attempts_total"],
                evidence=Evidence.APP_REPORTED,
                note=f"observed HTTP {conflict.status}",
            )
        )
    except MetricsContractError:
        pass

    return out


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=200)
    except Exception:
        return ""