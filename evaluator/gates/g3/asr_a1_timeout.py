"""ASR-A1 -- Availability > Detect Faults > Timeout.

Five seconds of latency are injected into the database path, then an uncached
product read is issued. The application should stop waiting well before the
database would have answered, exhaust its bounded retry policy, and return a
controlled failure.

Client-side elapsed time is the primary evidence, not timeouts_total. A system
that hangs for five seconds and then answers 504 has not detected anything; it
merely outlasted the fault. The stopwatch catches that, a counter would not.

The error code assertion is what keeps this scenario distinct from ASR-A3. Both
may answer 503, but only an exceeded time limit may call itself
DEPENDENCY_TIMEOUT -- if an application reports the same code for a refused
connection, the two tactics are indistinguishable and neither is demonstrated.
"""

from __future__ import annotations

import time
from typing import Any

from ...harness import trace
from ...harness.appmetrics import MetricsContractError
from ...harness.context import Context, SeedError
from ...harness.toxiproxy import ToxiproxyError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-A1"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_a1"]
    codes = ctx.thresholds["error_codes"]
    proxy = ctx.thresholds["toxiproxy"]["proxy_name"]
    started = time.monotonic()

    try:
        with trace.step("seed", "one product, then clear the cache so the read hits the database"):
            ctx.reset()
            product_id = ctx.seed_product(description="Timeout scenario product")
            ctx.reset()  # clear the cache so the read must reach the database
            before = ctx.metrics.read()
            trace.note(f"product={product_id}")
    except (SeedError, MetricsContractError) as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    # Client timeout sits above the budget so a hang is measured, not truncated:
    # cutting the request off ourselves would manufacture the very bound we are
    # trying to observe the application enforce.
    client_timeout = cfg["total_response_seconds_max"] * 2

    try:
        with ctx.toxi.latency(cfg["injected_latency_ms"], proxy=proxy):
            with trace.step(
                "uncached read under latency",
                f"expect {cfg['accepted_statuses']} / {codes['timeout']} within "
                f"{cfg['total_response_seconds_max']}s (client cutoff {client_timeout}s)",
            ):
                resp = ctx.http.get(
                    f"/api/v1/products/{product_id}", timeout_s=client_timeout
                )
                trace.response_line("read", resp, expected=cfg["accepted_statuses"])
    except ToxiproxyError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    elapsed_s = resp.elapsed_ms / 1000.0

    # Liveness is checked after the fault is removed: the process must have
    # survived detecting the fault, not merely reported one.
    with trace.step("liveness after the fault", "expect 200"):
        live = ctx.http.get("/health/live", timeout_s=5.0)
        trace.response_line("/health/live", live, expected=200)

    try:
        delta = ctx.metrics.read().delta(before)
        trace.note(f"metrics delta: {trace.brief(delta)}")
    except MetricsContractError as exc:
        delta = {}
        trace.note(f"metrics unavailable: {exc}")

    assertions: list[Assertion] = [
        assert_that(
            "response arrives within the bounded budget",
            elapsed_s <= cfg["total_response_seconds_max"],
            f"<= {cfg['total_response_seconds_max']}s",
            f"{elapsed_s:.2f}s",
            note="measured client-side; the injected latency is 5s, so waiting it out fails here",
        ),
        assert_that(
            "response is a controlled failure",
            resp.status in cfg["accepted_statuses"],
            f"one of {cfg['accepted_statuses']}",
            resp.status,
        ),
        assert_that(
            "failure is classified as a timeout",
            resp.error_code() == codes["timeout"],
            codes["timeout"],
            resp.error_code(),
            note="distinguishes detection of a slow dependency from an absent one",
        ),
        assert_that(
            "no request hangs past the budget",
            workload_hang(elapsed_s, cfg["total_response_seconds_max"]) == 0,
            cfg["hanging_requests_max"],
            workload_hang(elapsed_s, cfg["total_response_seconds_max"]),
        ),
        assert_that(
            "the application remains live",
            live.status == 200,
            200,
            live.status,
        ),
    ]

    if delta:
        assertions.append(
            assert_that(
                "timeouts_total increased",
                delta.get("timeouts_total", 0) >= 1,
                ">= 1",
                delta.get("timeouts_total", 0),
                evidence=Evidence.APP_REPORTED,
                note="corroborates the stopwatch; not decisive on its own",
            )
        )

    observations: dict[str, Any] = {
        "elapsed_s": round(elapsed_s, 3),
        "status": resp.status,
        "error_code": resp.error_code(),
        "timeouts_total_delta": delta.get("timeouts_total"),
        "attempts_delta": delta.get("db_product_read_attempts_total"),
        "live_after": live.status,
    }

    return ScenarioRun.from_assertions(
        ctx.app_id, SCENARIO_ID, run_index, assertions, observations,
        duration_s=time.monotonic() - started,
        logs_excerpt=_logs_if_failed(ctx, assertions),
    )


def workload_hang(elapsed_s: float, limit_s: float) -> int:
    return 1 if elapsed_s > limit_s else 0


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=200)
    except Exception:
        return ""
