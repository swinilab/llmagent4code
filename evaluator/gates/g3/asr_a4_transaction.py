"""ASR-A4 -- Availability > Prevent Faults > Transactions.

A fault is raised inside payment verification after the Payment row has been
changed but before the Invoice and Order changes and before commit. Either all
three updates land together or none of them do.

The decisive observations are read straight out of PostgreSQL rather than over
the API. Asking the application whether it rolled back would let a cache or an
in-memory shadow answer on the database's behalf; querying the rows directly
cannot be answered that way. transaction_rollbacks_total is recorded too, but
the verdict never rests on it.
"""

from __future__ import annotations

import time
from typing import Any

from ...harness import trace
from ...harness.context import Context, SeedError
from ...harness.pgprobe import SchemaDiscoveryError
from ...report.schema import Assertion, Evidence, ScenarioRun, assert_that

SCENARIO_ID = "ASR-A4"


def run(ctx: Context, run_index: int) -> ScenarioRun:
    cfg = ctx.thresholds["asr_a4"]
    codes = ctx.thresholds["error_codes"]
    started = time.monotonic()

    try:
        with trace.step("seed", "order driven to PENDING payment / ISSUED invoice / PAID order"):
            ctx.reset()
            chain = ctx.seed_to_payment()
            tables = _locate_tables(ctx)
            trace.note(
                f"order={chain.order_id} invoice={chain.invoice_id} payment={chain.payment_id}"
            )
            trace.note(f"tables: {trace.brief(tables)}")
    except (SeedError, SchemaDiscoveryError) as exc:
        trace.note(f"NOT_EXERCISABLE: {exc}")
        return ScenarioRun.not_exercisable(ctx.app_id, SCENARIO_ID, run_index, str(exc))

    before = _read_metrics(ctx)

    expected_rollback = cfg["post_rollback_state"]
    expected_final = cfg["post_success_state"]

    # ── stimulus: verification carrying the checkpoint fault ──────────────
    with trace.step(
        "verify with mid-transaction fault",
        f"X-Test-Fault: after-payment-update; expect "
        f"{cfg['accepted_fault_statuses']} / {codes['transaction']}",
    ):
        faulted = ctx.http.post(
            f"/api/v1/payments/{chain.payment_id}/verify",
            headers={"X-Test-Fault": "after-payment-update"},
        )
        trace.response_line("verify (faulted)", faulted, expected=cfg["accepted_fault_statuses"])

    with trace.step(
        "persisted state after the fault",
        f"read from PostgreSQL; expect {trace.brief(expected_rollback)}",
    ):
        post_fault = _persisted_state(ctx, tables, chain)
        trace.note(f"observed {trace.brief(post_fault)}")
    after_fault = _read_metrics(ctx)

    # ── recovery: the same request without the fault must succeed ─────────
    with trace.step("verify without the fault", "expect 200 and the full state transition"):
        clean = ctx.http.post(f"/api/v1/payments/{chain.payment_id}/verify")
        trace.response_line("verify (clean)", clean, expected=200)
        post_success = _persisted_state(ctx, tables, chain)
        trace.note(f"observed {trace.brief(post_success)}, expected {trace.brief(expected_final)}")

    assertions: list[Assertion] = [
        assert_that(
            "faulted request returns a controlled status",
            faulted.status in cfg["accepted_fault_statuses"],
            f"one of {cfg['accepted_fault_statuses']}",
            faulted.status,
        ),
        assert_that(
            "faulted response carries TRANSACTION_FAILED",
            faulted.error_code() == codes["transaction"],
            codes["transaction"],
            faulted.error_code(),
        ),
    ]

    # The heart of the scenario: three rows, one atomic unit.
    for entity in ("payment", "invoice", "order"):
        assertions.append(
            assert_that(
                f"{entity} rolled back to {expected_rollback[entity]}",
                post_fault[entity] == expected_rollback[entity],
                expected_rollback[entity],
                post_fault[entity],
                note="read directly from PostgreSQL",
            )
        )

    partial = _count_partial(post_fault, expected_rollback)
    assertions.append(
        assert_that(
            "no partially committed rows",
            partial <= cfg["partial_commits_max"],
            f"<= {cfg['partial_commits_max']}",
            partial,
            note="a nonzero count means the transaction boundary does not cover all three updates",
        )
    )

    assertions.append(
        assert_that(
            "subsequent verification succeeds",
            clean.status == 200,
            200,
            clean.status,
        )
    )
    for entity in ("payment", "invoice", "order"):
        assertions.append(
            assert_that(
                f"{entity} reaches {expected_final[entity]} after clean verification",
                post_success[entity] == expected_final[entity],
                expected_final[entity],
                post_success[entity],
                note="read directly from PostgreSQL",
            )
        )

    if before is not None and after_fault is not None:
        delta = after_fault.delta(before)["transaction_rollbacks_total"]
        assertions.append(
            assert_that(
                "transaction_rollbacks_total increased",
                delta >= 1,
                ">= 1",
                delta,
                evidence=Evidence.APP_REPORTED,
                note="corroborates the SQL-observed rollback; not decisive on its own",
            )
        )

    observations: dict[str, Any] = {
        "faulted_status": faulted.status,
        "faulted_error_code": faulted.error_code(),
        "post_fault_state": post_fault,
        "post_success_state": post_success,
        "partial_commits": partial,
        "clean_status": clean.status,
        "rollback_counter_delta": (
            after_fault.delta(before)["transaction_rollbacks_total"]
            if before is not None and after_fault is not None
            else None
        ),
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


# ── helpers ───────────────────────────────────────────────────────────────


def _locate_tables(ctx: Context) -> dict[str, str]:
    return {
        "payment": ctx.pg.find_table("payments", "payment", "oms_payments"),
        "invoice": ctx.pg.find_table("invoices", "invoice", "oms_invoices"),
        "order": ctx.pg.find_table("orders", "order", "oms_orders"),
    }


def _persisted_state(ctx: Context, tables: dict[str, str], chain: Any) -> dict[str, str | None]:
    """Read the three statuses from durable storage."""
    return {
        "payment": ctx.pg.entity_status(tables["payment"], chain.payment_id),
        "invoice": ctx.pg.entity_status(tables["invoice"], chain.invoice_id),
        "order": ctx.pg.entity_status(tables["order"], chain.order_id),
    }


def _count_partial(observed: dict[str, str | None], expected: dict[str, str]) -> int:
    """Count rows that moved when the transaction should have rolled back.

    Any nonzero result means part of the unit committed independently, which is
    the precise failure this tactic exists to prevent.
    """
    return sum(1 for k, want in expected.items() if observed.get(k) != want)


def _read_metrics(ctx: Context):
    try:
        return ctx.metrics.read()
    except Exception:
        return None


def _logs_if_failed(ctx: Context, assertions: list[Assertion]) -> str:
    if all(a.passed for a in assertions):
        return ""
    try:
        return ctx.compose.logs(tail=200)
    except Exception:
        return ""