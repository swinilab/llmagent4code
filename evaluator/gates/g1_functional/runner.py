"""G1 -- functional correctness.

Reports two figures that must not be collapsed into one, because they answer
different questions:

  * functional pass rate -- how much of the field-level contract holds
  * critical workflow pass -- whether the seven-step business process works
                              end to end, as a single yes/no

An application can score 90% on field validation while being unable to complete
an order, and that is a materially worse outcome than the percentage suggests.
Reporting only the rate would hide it.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from ...harness import trace
from ...harness.context import Context, SeedError
from ...report.schema import Assertion, Evidence, GateResult, assert_that
from .cases import (
    ENTITIES_WITH_ID_CHECKS,
    VALID_BODIES,
    Case,
    all_creation_cases,
    identifier_cases,
)
from .relational import RelationalCase, all_relational_cases


@dataclass
class CaseOutcome:
    case_id: str
    entity: str
    partition: str
    expected: int
    actual: int | None
    passed: bool
    note: str = ""


def run(ctx: Context) -> GateResult:
    outcomes: list[CaseOutcome] = []

    # The three case families run dozens of requests each. Reporting them
    # individually on the console would bury the gates that follow, so each
    # family is summarised and only its failures are named; every request is in
    # the trace log regardless.
    with trace.step("creation cases", "field-level validation on every create endpoint"):
        created = _run_creation_cases(ctx)
        _report_cases("creation", created)
        outcomes += created

    with trace.step("identifier cases", "existing, unknown and malformed ids on each read"):
        identified = _run_identifier_cases(ctx)
        _report_cases("identifier", identified)
        outcomes += identified

    with trace.step("relational cases", "cross-entity references and workflow preconditions"):
        relational = _run_relational_cases(ctx)
        _report_cases("relational", relational)
        outcomes += relational

    with trace.step("seven-step workflow", "PLACED -> ... -> CLOSED, including one illegal transition"):
        workflow_ok, workflow_detail = _run_seven_step_workflow(ctx)
        trace.expectation(
            "workflow", "order reaches CLOSED", workflow_detail, workflow_ok
        )

    with trace.step("cross-artifact consistency", "manifests, exported OpenAPI and live routes agree"):
        consistency = _check_api_consistency(ctx)
        trace.assertions(consistency)

    passed = sum(1 for o in outcomes if o.passed)
    total = len(outcomes)
    rate = passed / total if total else 0.0

    assertions: list[Assertion] = [
        assert_that(
            "functional case pass rate",
            rate >= 1.0,
            "100%",
            f"{rate:.1%} ({passed}/{total})",
            note="reported as a rate; the gate does not require perfection to continue",
        ),
        assert_that(
            "seven-step workflow completes",
            workflow_ok,
            "order reaches CLOSED",
            workflow_detail,
            note="a single yes/no: partial credit here would be misleading",
        ),
    ]
    assertions += consistency

    return GateResult(
        gate="G1",
        # The workflow is the gate's real bar. A system that cannot complete an
        # order has not implemented the domain, whatever its validation score.
        passed=workflow_ok and all(a.passed for a in consistency),
        assertions=assertions,
        details={
            "pass_rate": rate,
            "passed": passed,
            "total": total,
            "critical_workflow_pass": workflow_ok,
            "workflow_detail": workflow_detail,
            "by_entity": _group_by_entity(outcomes),
            "failures": [
                {
                    "case": o.case_id,
                    "entity": o.entity,
                    "partition": o.partition,
                    "expected": o.expected,
                    "actual": o.actual,
                }
                for o in outcomes
                if not o.passed
            ],
        },
    )


def _report_cases(family: str, outcomes: list[CaseOutcome]) -> None:
    """Summarise one family of cases, naming each failure.

    A pass rate alone is not actionable -- "83%" does not say which endpoint
    accepted a negative price -- so every failing case is printed with the
    status it was supposed to return and the one it did.
    """
    passed = sum(1 for o in outcomes if o.passed)
    trace.note(f"{family}: {passed}/{len(outcomes)} passed")
    for o in outcomes:
        if not o.passed:
            trace.expectation(
                f"{o.case_id} ({o.entity}/{o.partition})",
                o.expected,
                o.actual if o.actual is not None else o.note or "no response",
                False,
            )
    trace.tracer().emit(
        "case_family",
        family=family,
        passed=passed,
        total=len(outcomes),
        failures=[
            {"case": o.case_id, "entity": o.entity, "partition": o.partition,
             "expected": o.expected, "actual": o.actual, "note": o.note}
            for o in outcomes
            if not o.passed
        ],
    )


# ── case execution ────────────────────────────────────────────────────────


def _run_creation_cases(ctx: Context) -> list[CaseOutcome]:
    out: list[CaseOutcome] = []
    for case in all_creation_cases():
        body = copy.deepcopy(VALID_BODIES[case.entity])
        if case.mutate is not None:
            case.mutate(body)
        try:
            status = ctx.http.post(ctx.create_path(case.entity), json_body=body).status
        except SeedError as exc:
            out.append(CaseOutcome(case.id, case.entity, case.partition,
                                   case.expected_status, None, False, str(exc)))
            continue
        out.append(
            CaseOutcome(case.id, case.entity, case.partition, case.expected_status,
                        status, status == case.expected_status)
        )
    return out


def _run_identifier_cases(ctx: Context) -> list[CaseOutcome]:
    """Probe identifier handling on every entity's read endpoint.

    Each entity gets its own seeded resource so the existing-id probe is real
    rather than borrowed from another router.
    """
    out: list[CaseOutcome] = []
    for entity in ENTITIES_WITH_ID_CHECKS:
        try:
            seeded = _seed_one(ctx, entity)
        except SeedError as exc:
            for case in identifier_cases(entity):
                out.append(CaseOutcome(case.id, entity, case.partition,
                                       case.expected_status, None, False, str(exc)))
            continue

        base = ctx.create_path(entity)
        for case in identifier_cases(entity):
            ident = seeded if case.get_id == "<seeded>" else case.get_id
            if ident is None:
                continue
            status = ctx.http.get(f"{base}/{ident}").status
            out.append(
                CaseOutcome(case.id, entity, case.partition, case.expected_status,
                            status, status == case.expected_status)
            )
    return out


def _run_relational_cases(ctx: Context) -> list[CaseOutcome]:
    out: list[CaseOutcome] = []
    for case in all_relational_cases():
        try:
            status = case.execute(ctx)
        except SeedError as exc:
            out.append(CaseOutcome(case.id, case.entity, case.partition,
                                   case.expected_status, None, False, str(exc)))
            continue
        out.append(
            CaseOutcome(case.id, case.entity, case.partition, case.expected_status,
                        status, status == case.expected_status)
        )
    return out


def _seed_one(ctx: Context, entity: str) -> str:
    if entity == "customer":
        return ctx.seed_customer()
    if entity == "product":
        return ctx.seed_product()
    chain = ctx.seed_to_payment()
    return {"order": chain.order_id, "invoice": chain.invoice_id,
            "payment": chain.payment_id}[entity]


# ── the seven-step workflow ───────────────────────────────────────────────


def _run_seven_step_workflow(ctx: Context) -> tuple[bool, str]:
    """Drive one order from placement to closure, checking state at each step.

    Also probes one illegal transition -- shipping an order that has not been
    verified -- because a state machine that permits every transition would
    otherwise pass the happy path unnoticed.
    """
    try:
        chain = ctx.seed_to_payment()
    except SeedError as exc:
        return False, f"failed before verification: {exc}"

    def status_of(kind: str, ident: str) -> str | None:
        resp = ctx.http.get(f"/api/v1/{kind}/{ident}")
        return resp.body.get("status") if isinstance(resp.body, dict) else None

    # Steps 1-4 are covered by seeding; confirm where they left the order.
    if status_of("orders", chain.order_id) != "PAID":
        return False, f"after payment, order is {status_of('orders', chain.order_id)}, expected PAID"

    # An out-of-order transition must be refused.
    premature = ctx.http.post(f"/api/v1/orders/{chain.order_id}/ship")
    if premature.status != 409:
        return False, f"shipping an unverified order returned {premature.status}, expected 409"

    steps: list[tuple[str, str, str, str]] = [
        (f"/api/v1/payments/{chain.payment_id}/verify", "orders", chain.order_id, "VERIFIED"),
        (f"/api/v1/orders/{chain.order_id}/ship", "orders", chain.order_id, "SHIPPED"),
        (f"/api/v1/orders/{chain.order_id}/close", "orders", chain.order_id, "CLOSED"),
    ]
    for path, kind, ident, expected in steps:
        resp = ctx.http.post(path)
        if resp.status != 200:
            return False, f"{path} returned {resp.status}, expected 200"
        observed = status_of(kind, ident)
        if observed != expected:
            return False, f"after {path}, status is {observed}, expected {expected}"

    # Verification is atomic across three entities; confirm the other two moved.
    if status_of("payments", chain.payment_id) != "VERIFIED":
        return False, "payment did not reach VERIFIED"
    if status_of("invoices", chain.invoice_id) != "PAID":
        return False, "invoice did not reach PAID"

    return True, "PLACED -> ACCEPTED -> INVOICED -> PAID -> VERIFIED -> SHIPPED -> CLOSED"


# ── cross-artifact consistency ────────────────────────────────────────────


def _check_api_consistency(ctx: Context) -> list[Assertion]:
    """Confirm the manifests, the exported OpenAPI and the live routes agree.

    A contradiction here is a defect in its own right: it means an external
    consumer following the documentation would call an endpoint that does not
    exist, or miss one that does.
    """
    out: list[Assertion] = []
    app_dir = ctx.compose.app_dir

    try:
        manifest = ctx.manifest()
    except SeedError as exc:
        return [assert_that("create_apis.json is readable", False, "valid JSON", str(exc),
                            evidence=Evidence.ARTIFACT)]

    runtime = ctx.http.get("/openapi.json")
    runtime_paths: set[str] = set()
    if runtime.status == 200 and isinstance(runtime.body, dict):
        runtime_paths = set(runtime.body.get("paths", {}))
    out.append(
        assert_that("/openapi.json is served", runtime.status == 200, 200, runtime.status)
    )

    # Every declared create path must exist among the running routes.
    for entity, entry in manifest.items():
        path = entry.get("path", "")
        out.append(
            assert_that(
                f"create path for {entity} is a live route",
                path in runtime_paths if runtime_paths else False,
                f"{path} present in /openapi.json",
                "present" if path in runtime_paths else "absent",
                evidence=Evidence.ARTIFACT,
            )
        )

    # The exported file must match what the application actually serves.
    exported_file = app_dir / "openapi.json"
    if exported_file.is_file() and runtime_paths:
        try:
            exported_paths = set(json.loads(exported_file.read_text(encoding="utf-8"))["paths"])
            drift = exported_paths.symmetric_difference(runtime_paths)
            out.append(
                assert_that(
                    "exported openapi.json matches the running routes",
                    not drift,
                    "no difference",
                    f"{len(drift)} differing paths: {sorted(drift)[:5]}",
                    evidence=Evidence.ARTIFACT,
                )
            )
        except (ValueError, KeyError) as exc:
            out.append(assert_that("exported openapi.json is parseable", False,
                                   "valid OpenAPI", str(exc), evidence=Evidence.ARTIFACT))
    else:
        out.append(assert_that("openapi.json exists at the repository root",
                               exported_file.is_file(), "present",
                               "present" if exported_file.is_file() else "absent",
                               evidence=Evidence.ARTIFACT))

    # Workflow manifest paths must resolve too, allowing for {id} templating.
    wf_file = app_dir / "workflow_apis.json"
    if wf_file.is_file() and runtime_paths:
        try:
            wf = json.loads(wf_file.read_text(encoding="utf-8"))
            for op, entry in wf.items():
                template = str(entry.get("pathTemplate", ""))
                out.append(
                    assert_that(
                        f"workflow route {op} is live",
                        _template_matches(template, runtime_paths),
                        template,
                        "matched" if _template_matches(template, runtime_paths) else "no match",
                        evidence=Evidence.ARTIFACT,
                    )
                )
        except ValueError as exc:
            out.append(assert_that("workflow_apis.json is parseable", False,
                                   "valid JSON", str(exc), evidence=Evidence.ARTIFACT))
    else:
        out.append(assert_that("workflow_apis.json exists", wf_file.is_file(), "present",
                               "present" if wf_file.is_file() else "absent",
                               evidence=Evidence.ARTIFACT))

    return out


def _template_matches(template: str, runtime_paths: set[str]) -> bool:
    """Compare a manifest template against OpenAPI paths.

    Both use brace placeholders but need not agree on the parameter's name --
    /orders/{id}/ship and /orders/{order_id}/ship describe the same route -- so
    placeholders are normalised before comparison.
    """
    import re

    norm = lambda s: re.sub(r"\{[^}]*\}", "{}", s)
    target = norm(template)
    return any(norm(p) == target for p in runtime_paths)


def _group_by_entity(outcomes: list[CaseOutcome]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for o in outcomes:
        bucket = grouped.setdefault(o.entity, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if o.passed:
            bucket["passed"] += 1
    for bucket in grouped.values():
        bucket["rate"] = bucket["passed"] / bucket["total"] if bucket["total"] else 0.0
    return grouped
