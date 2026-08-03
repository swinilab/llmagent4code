"""ASR-P2 -- Performance > Control Resource Demand > Limit Event Response.

Two hundred product searches are fired simultaneously, each holding an admitted
slot for 250 ms, against a system configured to admit ten at a time. The system
should serve what it admitted and refuse the rest immediately.

The rejection latency measure is what separates this tactic from bounded
queueing, and it is the reason no client-side concurrency limit is applied here:
throttling from our side would perform the server's admission control for it. A
system that queues the excess still answers 503 eventually, but it answers
slowly, and the p95-of-rejections assertion is what catches that.

That measure is taken relative to a floor rather than absolutely. Opening two
hundred sockets simultaneously is not free, and on some hosts it costs more than
the entire rejection budget -- a calibration run measured 1.4 s p95 against
`/health/live`, a path that does no work at all, while the server was in fact
refusing in about nine milliseconds. Charging that to the application would fail
a correct implementation for the harness's own overhead, so the same burst is
first fired at an exempt no-op path and only the excess above it is attributed
to admission control.

Readiness is polled during the burst as well as after it. The specification puts
the health paths outside admission control, so a 429 from /health/ready is not a
measurement problem -- it is the application routing its own observability
through the mechanism it was told to keep separate.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from ...harness import trace
from ...harness.appmetrics import MetricsContractError
from ...harness.context import Context, SeedError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-P2"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_p2"]
    codes = ctx.thresholds["error_codes"]
    started = time.monotonic()

    try:
        with trace.step("seed", "one product to search for"):
            ctx.reset()
            ctx.seed_product(description="Overload scenario product")
            before = ctx.metrics.read()
    except (SeedError, MetricsContractError) as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    restarts_before = ctx.compose.total_restarts()

    # Establish what a burst of this size costs the client before blaming the
    # server for any of it. Opening two hundred sockets at once is expensive,
    # and on some hosts that cost alone exceeds the rejection budget -- so the
    # same burst is first fired at an exempt path that does no work. Whatever
    # that costs is the floor, and only latency above it can be attributed to
    # admission control.
    with trace.step(
        "client floor",
        f"same burst of {cfg['concurrent_requests']} against the exempt /health/live",
    ):
        baseline = ctx.http.run_simultaneous(
            "GET", "/health/live", total=cfg["concurrent_requests"], timeout_s=30.0
        )
        client_floor_ms = baseline.p95_ms()
        trace.summarise_workload("baseline burst", baseline)
        trace.note(f"client floor p95 = {client_floor_ms:.0f}ms; subtracted from the measurement")

    with trace.step(
        "overload burst",
        f"{cfg['concurrent_requests']} simultaneous searches, "
        f"X-Test-Delay-Ms={cfg['test_delay_ms']}; expect >= {cfg['successes_min']} served "
        f"and >= {cfg['controlled_rejections_min']} refused with {codes['overload']}",
    ):
        # Sample health concurrently with the burst; see module docstring.
        health_probe = _HealthProbe(ctx)
        health_probe.start()

        workload = ctx.http.run_simultaneous(
            "GET",
            "/api/v1/products?query=overload",
            total=cfg["concurrent_requests"],
            headers={"X-Test-Delay-Ms": str(cfg["test_delay_ms"])},
            timeout_s=30.0,
        )

        health_probe.stop()
        trace.summarise_workload("burst", workload)

    with trace.step("readiness recovery", f"limit {cfg['ready_recovery_seconds_max']}s"):
        ready_recovery = _time_to_ready(ctx, cfg["ready_recovery_seconds_max"])
        trace.note(
            f"ready after {ready_recovery:.1f}s" if ready_recovery is not None
            else "never became ready"
        )
    restarts_after = ctx.compose.total_restarts()

    try:
        delta = ctx.metrics.read().delta(before)
        trace.note(f"metrics delta: {trace.brief(delta)}")
    except MetricsContractError:
        delta = {}

    successes = workload.successes()
    rejections = workload.with_status(429, 503)
    rejection_p95 = workload.percentile_ms(95, subset=rejections) if rejections else 0.0
    unhandled = workload.unhandled_500s()

    retry_after_present = sum(
        1 for r in rejections if r.status == 429 and "retry-after" in {k.lower() for k in r.headers}
    )
    correct_code = sum(1 for r in rejections if r.error_code() == codes["overload"])

    assertions: list[Assertion] = [
        assert_that(
            "at least one request is served",
            len(successes) >= cfg["successes_min"],
            f">= {cfg['successes_min']}",
            len(successes),
            note="refusing everything is not admission control",
        ),
        assert_that(
            "excess work is refused in a controlled way",
            len(rejections) >= cfg["controlled_rejections_min"],
            f">= {cfg['controlled_rejections_min']}",
            len(rejections),
        ),
        assert_that(
            "rejections are immediate",
            max(0.0, rejection_p95 - client_floor_ms) <= cfg["rejection_p95_ms_max"],
            f"<= {cfg['rejection_p95_ms_max']} ms above the client floor",
            f"{rejection_p95:.0f} ms measured, {client_floor_ms:.0f} ms floor,"
            f" {max(0.0, rejection_p95 - client_floor_ms):.0f} ms attributable",
            note="the floor is the same burst against an exempt no-op path; without "
            "subtracting it the measurement charges the server for the cost of "
            "opening two hundred sockets, which on some hosts exceeds the whole budget",
        ),
        assert_that(
            "429 responses carry Retry-After",
            retry_after_present == len(workload.with_status(429)),
            f"{len(workload.with_status(429))} of {len(workload.with_status(429))}",
            retry_after_present,
        ),
        assert_that(
            "rejections carry OVERLOAD_REJECTED",
            correct_code == len(rejections) if rejections else False,
            f"{len(rejections)}",
            correct_code,
        ),
        assert_that(
            "no unhandled 500s",
            unhandled <= cfg["unhandled_500_max"],
            cfg["unhandled_500_max"],
            unhandled,
        ),
        assert_that(
            "no container restarts",
            restarts_after - restarts_before <= cfg["restart_count_max"],
            cfg["restart_count_max"],
            restarts_after - restarts_before,
            note="docker inspect; surviving overload by crashing does not count as surviving it",
        ),
        assert_that(
            "readiness returns within the recovery window",
            ready_recovery is not None and ready_recovery <= cfg["ready_recovery_seconds_max"],
            f"<= {cfg['ready_recovery_seconds_max']}s",
            f"{ready_recovery:.2f}s" if ready_recovery is not None else "never",
        ),
        assert_that(
            "health stayed outside admission control",
            not health_probe.rejected_statuses,
            "never 429/503",
            f"observed {sorted(set(health_probe.rejected_statuses))}"
            if health_probe.rejected_statuses
            else "never rejected",
            note="the specification exempts observation paths from admission control",
        ),
        assert_that(
            "health kept answering throughout the burst",
            not any(s is None for s in health_probe.all_statuses),
            "a response to every probe",
            f"{sum(1 for s in health_probe.all_statuses if s is None)}"
            f" of {len(health_probe.all_statuses)} probes unanswered",
            note="losing the observation path under load is itself the defect, "
            "not merely an obstacle to measuring one",
        ),
    ]

    if delta:
        assertions.append(
            assert_that(
                "requests_rejected_total matches observed rejections",
                _agrees(delta.get("requests_rejected_total", 0), len(rejections)),
                len(rejections),
                delta.get("requests_rejected_total", 0),
                evidence=Evidence.APP_REPORTED,
            )
        )

    observations: dict[str, Any] = {
        "successes": len(successes),
        "controlled_rejections": len(rejections),
        "rejection_p95_ms": round(rejection_p95, 1),
        "client_floor_p95_ms": round(client_floor_ms, 1),
        "rejection_p95_above_floor_ms": round(max(0.0, rejection_p95 - client_floor_ms), 1),
        "unhandled_500s": unhandled,
        "restart_delta": restarts_after - restarts_before,
        "ready_recovery_s": round(ready_recovery, 2) if ready_recovery is not None else None,
        "status_distribution": workload.status_distribution(),
        "requests_rejected_total_delta": delta.get("requests_rejected_total"),
        # A probe that got no response at all records None, which cannot be
        # ordered against a status code -- and "health stopped answering" is
        # itself a finding worth keeping rather than discarding.
        "health_probe_statuses": sorted(
            {s for s in health_probe.all_statuses if s is not None}
        ),
        "health_probe_unanswered": sum(1 for s in health_probe.all_statuses if s is None),
    }

    return ScenarioRun.from_assertions(
        ctx.app_id, SCENARIO_ID, run_index, assertions, observations,
        duration_s=time.monotonic() - started,
        logs_excerpt=_logs_if_failed(ctx, assertions),
    )


class _HealthProbe(threading.Thread):
    """Polls /health/ready in the background for the duration of the burst.

    The stop flag is deliberately not named `_stop`: threading.Thread already
    defines that internally, and shadowing it replaces a method the base class
    calls with an Event, which fails only once the thread is actually torn down.
    """

    def __init__(self, ctx: Context, interval_s: float = 0.25):
        super().__init__(daemon=True)
        self._ctx = ctx
        self._interval = interval_s
        self._halt = threading.Event()
        self.all_statuses: list[int | None] = []
        self.rejected_statuses: list[int] = []

    def run(self) -> None:
        while not self._halt.is_set():
            resp = self._ctx.http.get("/health/ready", timeout_s=3.0)
            self.all_statuses.append(resp.status)
            if resp.status in (429, 503):
                self.rejected_statuses.append(resp.status)
            self._halt.wait(self._interval)

    def stop(self) -> None:
        self._halt.set()
        self.join(timeout=5.0)


def _time_to_ready(ctx: Context, limit_s: float) -> float | None:
    """Seconds until /health/ready answers 200 after the load stops."""
    deadline = time.monotonic() + limit_s + 3.0
    start = time.monotonic()
    while time.monotonic() < deadline:
        if ctx.http.get("/health/ready", timeout_s=3.0).status == 200:
            return time.monotonic() - start
        time.sleep(0.1)
    return None


def _agrees(reported: int, observed: int, tolerance: int = 5) -> bool:
    return abs(reported - observed) <= tolerance


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=200)
    except Exception:
        return ""
