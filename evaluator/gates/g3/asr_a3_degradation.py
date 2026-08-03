"""ASR-A3 -- Availability > Recover from Faults > Graceful Degradation.

The proxy is disabled for sixty seconds. Three capabilities are exercised
during the outage, and they are meant to behave differently:

  * the warmed product read must keep succeeding from the maintained copy;
  * the unwarmed product read must fail in a controlled way, because there is
    no copy to serve and the database is gone;
  * writes must fail in a controlled way, because durable state is unavailable.

The three-way split is the whole point. An application that fails everything is
not degrading gracefully, it is simply down; one that succeeds at everything is
fabricating data or lying about writes. Both are caught here, which is why the
unwarmed read and the write attempts are asserted as positively as the warmed
read is.

Recovery is timed to a real business write rather than to /health/ready.
Readiness is the application's own opinion of itself and can be optimistic; a
write that lands in PostgreSQL cannot be.
"""

from __future__ import annotations

import time
from typing import Any

from ...harness import trace
from ...harness.context import Context, SeedError
from ...harness.httpclient import Workload
from ...harness.toxiproxy import ToxiproxyError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-A3"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_a3"]
    codes = ctx.thresholds["error_codes"]
    proxy = ctx.thresholds["toxiproxy"]["proxy_name"]
    started = time.monotonic()

    try:
        with trace.step("seed", "two products (one to be warmed) and a customer"):
            ctx.reset()
            warmed_id = ctx.seed_product(description="Warmed product for outage")
            unwarmed_id = ctx.seed_product(description="Unwarmed product for outage")
            customer_id = ctx.seed_customer()
            trace.note(f"warmed={warmed_id} unwarmed={unwarmed_id} customer={customer_id}")
    except SeedError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    # Warm exactly one of the two products. The other is the control.
    with trace.step("warm cache", f"GET /api/v1/products/{warmed_id} before the outage"):
        warm = ctx.http.get(f"/api/v1/products/{warmed_id}")
        trace.response_line("warm read", warm, expected=200)
    if warm.status != 200:
        return ScenarioRun.not_exercisable(
            ctx.app_id, SCENARIO_ID, run_index, "could not warm the product cache"
        )

    restarts_before = ctx.compose.total_restarts()
    outage_s = cfg["outage_seconds"]

    try:
        with ctx.toxi.outage(proxy=proxy):
            outage_started = time.monotonic()

            # Observation paths must survive the outage; sampled early, while
            # the fault is unambiguously active.
            with trace.step("observability during outage", "metrics and health must still answer"):
                metrics_reachable = ctx.metrics.reachable_during_fault()
                live_answered, live_status = ctx.metrics.health_reachable("/health/live")
                ready_answered, ready_status = ctx.metrics.health_reachable("/health/ready")
                trace.note(
                    f"metrics={'reachable' if metrics_reachable else 'unreachable'} "
                    f"live={live_status if live_answered else 'no response'} "
                    f"ready={ready_status if ready_answered else 'no response'}"
                )

            with trace.step(
                "unwarmed read",
                f"expect controlled failure {cfg['accepted_read_statuses']} / "
                f"{codes['unavailable']}",
            ):
                unwarmed = ctx.http.get(f"/api/v1/products/{unwarmed_id}", timeout_s=15.0)
                trace.response_line(
                    "unwarmed read", unwarmed, expected=cfg["accepted_read_statuses"]
                )

            with trace.step(
                "writes during outage",
                f"{cfg['state_changing_requests']} creates; expect "
                f"{cfg['accepted_write_statuses']} / {codes['unavailable']}",
            ):
                writes = [
                    ctx.http.post(
                        ctx.create_path("product"),
                        json_body={
                            "description": f"Write during outage {i}",
                            "price": {"amount": "5.00", "currency": "USD"},
                        },
                        timeout_s=15.0,
                    )
                    for i in range(cfg["state_changing_requests"])
                ]
                trace.summarise_workload("writes", _as_workload(writes))

            # Spread the warmed reads across whatever outage time remains.
            remaining = max(0.0, outage_s - (time.monotonic() - outage_started))
            pause = remaining / cfg["warmed_reads"] if cfg["warmed_reads"] else 0.0
            with trace.step(
                "warmed reads",
                f"{cfg['warmed_reads']} reads over the remaining {remaining:.0f}s; expect "
                f">= {cfg['warmed_success_rate_min']:.0%} success",
            ):
                warmed = ctx.http.run_sequential(
                    "GET",
                    f"/api/v1/products/{warmed_id}",
                    total=cfg["warmed_reads"],
                    pause_s=min(pause, 0.1),
                )
                trace.summarise_workload("warmed reads", warmed)

            # Hold the outage open for its full declared duration so recovery is
            # measured from a consistent starting condition.
            leftover = outage_s - (time.monotonic() - outage_started)
            if leftover > 0:
                time.sleep(leftover)

        with trace.step(
            "recovery", f"time to first successful write; limit {cfg['recovery_seconds_max']}s"
        ):
            recovery_s = _time_to_first_successful_write(
                ctx, customer_id, cfg["recovery_seconds_max"]
            )
            trace.note(
                f"recovered in {recovery_s:.1f}s" if recovery_s is not None else "never recovered"
            )
    except ToxiproxyError as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    restarts_after = ctx.compose.total_restarts()
    with trace.step("post-recovery smoke", "full order workflow must operate normally"):
        smoke_ok, smoke_detail = _post_recovery_smoke(ctx)
        trace.note(smoke_detail)

    warmed_rate = warmed.success_rate()
    warmed_p95 = warmed.p95_ms()
    controlled_writes = sum(1 for w in writes if w.status in cfg["accepted_write_statuses"])
    correct_write_code = sum(1 for w in writes if w.error_code() == codes["unavailable"])
    unhandled = warmed.unhandled_500s() + sum(
        1 for w in writes if w.status == 500 and w.error_code() != "TRANSACTION_FAILED"
    )

    assertions: list[Assertion] = [
        assert_that(
            "warmed reads stay available",
            warmed_rate >= cfg["warmed_success_rate_min"],
            f">= {cfg['warmed_success_rate_min']:.0%}",
            f"{warmed_rate:.1%}",
            note="served from data populated before the outage",
        ),
        assert_that(
            "warmed reads stay fast",
            warmed_p95 <= cfg["warmed_p95_ms_max"],
            f"<= {cfg['warmed_p95_ms_max']} ms",
            f"{warmed_p95:.0f} ms",
        ),
        assert_that(
            "the unwarmed read fails in a controlled way",
            unwarmed.status in cfg["accepted_read_statuses"],
            f"one of {cfg['accepted_read_statuses']}",
            unwarmed.status,
            note="no copy exists, so this must not succeed; fabricated data would show up here",
        ),
        assert_that(
            "the unwarmed read is classified as unavailable",
            unwarmed.error_code() == codes["unavailable"],
            codes["unavailable"],
            unwarmed.error_code(),
            note="distinguishes an absent dependency from a slow one",
        ),
        assert_that(
            "writes fail safely",
            controlled_writes == len(writes),
            len(writes),
            controlled_writes,
            note="reporting success without durable state would be worse than failing",
        ),
        assert_that(
            "write failures are classified as unavailable",
            correct_write_code == len(writes),
            len(writes),
            correct_write_code,
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
        ),
        assert_that(
            "metrics stayed reachable during the outage",
            metrics_reachable,
            "200",
            "reachable" if metrics_reachable else "unreachable",
            note="an application must not route its own observability through the failed dependency",
        ),
        assert_that(
            "liveness stayed reachable during the outage",
            live_answered and live_status == 200,
            200,
            live_status if live_answered else "no response",
        ),
        assert_that(
            "readiness still answered during the outage",
            ready_answered,
            "any response",
            ready_status if ready_answered else "no response",
            note="reporting unready is correct here; failing to answer at all is not",
        ),
        assert_that(
            "service recovers after the database returns",
            recovery_s is not None and recovery_s <= cfg["recovery_seconds_max"],
            f"<= {cfg['recovery_seconds_max']}s",
            f"{recovery_s:.1f}s" if recovery_s is not None else "never recovered",
            note="timed to a successful business write, not to self-reported readiness",
        ),
        assert_that(
            "post-recovery smoke tests pass",
            smoke_ok,
            "workflow operates normally",
            smoke_detail,
        ),
    ]

    observations: dict[str, Any] = {
        "warmed_success_rate": round(warmed_rate, 4),
        "warmed_p95_ms": round(warmed_p95, 1),
        "warmed_status_distribution": warmed.status_distribution(),
        "unwarmed_status": unwarmed.status,
        "unwarmed_error_code": unwarmed.error_code(),
        "controlled_writes": controlled_writes,
        "write_status_distribution": _distribution(writes),
        "unhandled_500s": unhandled,
        "restart_delta": restarts_after - restarts_before,
        "recovery_s": round(recovery_s, 2) if recovery_s is not None else None,
        "metrics_reachable_during_outage": metrics_reachable,
        "smoke_ok": smoke_ok,
    }

    return ScenarioRun.from_assertions(
        ctx.app_id, SCENARIO_ID, run_index, assertions, observations,
        duration_s=time.monotonic() - started,
        logs_excerpt=_logs_if_failed(ctx, assertions),
    )


def _time_to_first_successful_write(
    ctx: Context, customer_id: str, limit_s: float
) -> float | None:
    """Seconds until a real write lands after the proxy is re-enabled.

    Anchored on a write rather than on readiness because readiness is the
    application's own claim about itself, while a persisted row is a fact.
    """
    deadline = time.monotonic() + limit_s + 5.0
    start = time.monotonic()
    while time.monotonic() < deadline:
        resp = ctx.http.post(
            ctx.create_path("product"),
            json_body={
                "description": "Recovery probe product",
                "price": {"amount": "1.00", "currency": "USD"},
            },
            timeout_s=5.0,
        )
        if resp.status == 201:
            return time.monotonic() - start
        time.sleep(0.25)
    return None


def _post_recovery_smoke(ctx: Context) -> tuple[bool, str]:
    """Confirm the full workflow still operates once the database is back."""
    try:
        chain = ctx.seed_to_payment()
    except SeedError as exc:
        return False, f"workflow seeding failed: {exc}"

    verify = ctx.http.post(f"/api/v1/payments/{chain.payment_id}/verify")
    if verify.status != 200:
        return False, f"payment verification returned {verify.status}"

    order = ctx.http.get(f"/api/v1/orders/{chain.order_id}")
    status = order.body.get("status") if isinstance(order.body, dict) else None
    if status != "VERIFIED":
        return False, f"order is {status} after verification, expected VERIFIED"
    return True, "order created, invoiced, paid and verified after recovery"


def _distribution(responses: list) -> dict[str | int, int]:
    from collections import Counter

    return dict(Counter(r.status if r.status is not None else "transport_error" for r in responses))


def _as_workload(responses: list) -> Workload:
    """View a hand-built list of responses through the aggregate interface.

    The writes are issued one at a time rather than through a workload helper,
    but the trace should describe them the same way it describes every other
    batch -- count, status spread, latency -- so they are wrapped rather than
    given a second, differently-shaped summary line.
    """
    return Workload(list(responses))


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=300)
    except Exception:
        return ""
