"""G2 -- traceability and observability-contract validation.

Two independent things are checked, and the distinction matters for what may be
claimed from the result.

G2.1 resolves nfr-trace.json against the delivered source: do the six entries
exist, do they name the prescribed tactics verbatim, and do the files and
functions they cite actually exist? This establishes artifact-level consistency
only. A function can exist, be named plausibly, and do nothing -- so G2 must
never be read as evidence that a tactic works. That is what G3 is for.

G2.2 checks the observability contract: metrics schema, reset endpoint, test
hooks, health paths. A gap here makes the dependent scenario NOT_EXERCISABLE
rather than FAIL, because an interface we cannot drive tells us nothing about
whether the mechanism behind it exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..common.trace_check import function_exists
from ..harness.appmetrics import REQUIRED_KEYS, AppMetrics, MetricsContractError
from ..harness.httpclient import HttpHarness
from ..report.schema import Assertion, Evidence, GateResult, assert_that

SCENARIO_ORDER = ("ASR-P1", "ASR-P2", "ASR-A1", "ASR-A2", "ASR-A3", "ASR-A4")

# The six prescribed tactic strings, exactly as the specification writes them.
# Compared verbatim: the specification forbids paraphrase, and near-misses like
# "Degradation" for "Graceful Degradation" are precisely what this catches.
EXPECTED_TACTICS = {
    "ASR-P1": "Performance > Manage Resources > Maintain Multiple Copies of Data",
    "ASR-P2": "Performance > Control Resource Demand > Manage Work Requests > Limit Event Response",
    "ASR-A1": "Availability > Detect Faults > Timeout",
    "ASR-A2": "Availability > Recover from Faults > Preparation and Repair > Retry",
    "ASR-A3": "Availability > Recover from Faults > Preparation and Repair > Graceful Degradation",
    "ASR-A4": "Availability > Prevent Faults > Transactions",
}

REQUIRED_ENTRY_KEYS = (
    "scenarioId", "nfr", "tacticUsed", "filesImplemented",
    "functionNames", "configurationKeys", "librariesUsed", "metrics", "verificationMethod",
)


@dataclass
class TraceIssue:
    scenario: str
    kind: str
    detail: str


def run(app_dir: Path, base_url: str, thresholds: dict) -> GateResult:
    assertions: list[Assertion] = []
    details: dict[str, Any] = {}

    trace_assertions, issues, resolved = _check_traceability(app_dir)
    assertions += trace_assertions
    details["traceability_issues"] = [vars(i) for i in issues]
    details["resolved_references"] = resolved

    interface_assertions, exercisable = _check_observability(base_url, thresholds)
    assertions += interface_assertions
    details["exercisable_scenarios"] = exercisable

    return GateResult("G2", all(a.passed for a in assertions), assertions, details)


# ── G2.1 traceability ─────────────────────────────────────────────────────


def _check_traceability(app_dir: Path) -> tuple[list[Assertion], list[TraceIssue], dict]:
    out: list[Assertion] = []
    issues: list[TraceIssue] = []
    resolved = {"files": 0, "files_missing": 0, "functions": 0, "functions_missing": 0}

    path = app_dir / "nfr-trace.json"
    if not path.is_file():
        return (
            [assert_that("nfr-trace.json exists", False, "present", "absent",
                         evidence=Evidence.ARTIFACT)],
            issues,
            resolved,
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["nfrTrace"]
    except (ValueError, KeyError, TypeError) as exc:
        return (
            [assert_that("nfr-trace.json has an nfrTrace array", False,
                         "parseable with nfrTrace", str(exc)[:200],
                         evidence=Evidence.ARTIFACT)],
            issues,
            resolved,
        )

    by_id = {str(e.get("scenarioId")): e for e in entries if isinstance(e, dict)}

    out.append(
        assert_that("exactly six ASR entries", len(entries) == 6, 6, len(entries),
                    evidence=Evidence.ARTIFACT)
    )
    missing_ids = [s for s in SCENARIO_ORDER if s not in by_id]
    out.append(
        assert_that("all six scenario ids present", not missing_ids,
                    list(SCENARIO_ORDER), f"missing {missing_ids}" if missing_ids else "all present",
                    evidence=Evidence.ARTIFACT)
    )

    for scenario in SCENARIO_ORDER:
        entry = by_id.get(scenario)
        if entry is None:
            continue

        absent_keys = [k for k in REQUIRED_ENTRY_KEYS if k not in entry]
        if absent_keys:
            issues.append(TraceIssue(scenario, "missing_keys", str(absent_keys)))

        # Verbatim tactic comparison -- paraphrase is explicitly forbidden.
        claimed = str(entry.get("tacticUsed", ""))
        expected = EXPECTED_TACTICS[scenario]
        out.append(
            assert_that(
                f"{scenario} cites the prescribed tactic verbatim",
                claimed == expected,
                expected,
                claimed or "(absent)",
                evidence=Evidence.ARTIFACT,
            )
        )

        for rel in entry.get("filesImplemented", []) or []:
            if (app_dir / str(rel)).is_file():
                resolved["files"] += 1
            else:
                resolved["files_missing"] += 1
                issues.append(TraceIssue(scenario, "file_not_found", str(rel)))

        for ref in entry.get("functionNames", []) or []:
            if function_exists(app_dir, str(ref)):
                resolved["functions"] += 1
            else:
                resolved["functions_missing"] += 1
                issues.append(TraceIssue(scenario, "function_not_found", str(ref)))

        # Metric names must be ones the endpoint actually exposes; citing a
        # metric that does not exist is an unverifiable claim.
        for metric in entry.get("metrics", []) or []:
            if str(metric) not in REQUIRED_KEYS:
                issues.append(TraceIssue(scenario, "unknown_metric", str(metric)))

    out.append(
        assert_that(
            "every cited file resolves",
            resolved["files_missing"] == 0,
            0,
            resolved["files_missing"],
            evidence=Evidence.ARTIFACT,
            note=f"{resolved['files']} resolved",
        )
    )
    out.append(
        assert_that(
            "every cited function resolves",
            resolved["functions_missing"] == 0,
            0,
            resolved["functions_missing"],
            evidence=Evidence.ARTIFACT,
            note=f"{resolved['functions']} resolved; existence only, not effectiveness",
        )
    )
    unknown_metrics = [i for i in issues if i.kind == "unknown_metric"]
    out.append(
        assert_that("cited metrics are ones the endpoint exposes", not unknown_metrics,
                    "all known", f"{len(unknown_metrics)} unknown", evidence=Evidence.ARTIFACT)
    )

    out.append(_tactics_consistent_across_documents(app_dir))
    return out, issues, resolved


def _tactics_consistent_across_documents(app_dir: Path) -> Assertion:
    """The ADRs and the Markdown matrix must not contradict the JSON.

    Checked by presence of each verbatim tactic string in both prose documents.
    A tactic named one way in the JSON and another way in the ADR is exactly the
    inconsistency this gate exists to surface.
    """
    adr = _read(app_dir / "architecture" / "ADRs.md")
    matrix = _read(app_dir / "architecture" / "tactic-traceability.md")
    if not adr or not matrix:
        return assert_that(
            "ADRs and traceability matrix are present", False,
            "both files readable",
            f"ADRs={'yes' if adr else 'no'}, matrix={'yes' if matrix else 'no'}",
            evidence=Evidence.ARTIFACT,
        )

    missing_adr = [t for t in EXPECTED_TACTICS.values() if t not in adr]
    missing_matrix = [t for t in EXPECTED_TACTICS.values() if t not in matrix]
    ok = not missing_adr and not missing_matrix
    return assert_that(
        "ADRs and matrix name all six tactics verbatim",
        ok,
        "all six in both documents",
        f"absent from ADRs: {len(missing_adr)}, from matrix: {len(missing_matrix)}",
        evidence=Evidence.ARTIFACT,
    )


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ── G2.2 observability contract ───────────────────────────────────────────


def _check_observability(base_url: str, thresholds: dict) -> tuple[list[Assertion], dict]:
    out: list[Assertion] = []
    http = HttpHarness(base_url)
    metrics = AppMetrics(base_url)
    exercisable: dict[str, bool] = {}

    # Metrics schema -- P1, P2, A1, A2 and A4 all read counters from here.
    try:
        metrics.read()
        schema_ok, schema_detail = True, f"all {len(REQUIRED_KEYS)} keys, integer-valued"
    except MetricsContractError as exc:
        schema_ok, schema_detail = False, str(exc)
    out.append(
        assert_that("/internal/metrics satisfies its schema", schema_ok,
                    f"{len(REQUIRED_KEYS)} integer keys", schema_detail)
    )

    # Reset endpoint -- every scenario depends on a clean starting point.
    try:
        metrics.reset()
        reset_ok, reset_detail = True, "204"
    except MetricsContractError as exc:
        reset_ok, reset_detail = False, str(exc)
    out.append(
        assert_that("/internal/test/reset returns 204", reset_ok, 204, reset_detail)
    )

    # Test hooks must be active, or P2, A2 and A4 have no stimulus at all.
    delay = http.get("/api/v1/products?query=hook-probe", headers={"X-Test-Delay-Ms": "200"})
    hooks_ok = delay.status is not None and delay.status < 500
    out.append(
        assert_that("X-Test-Delay-Ms is accepted without error", hooks_ok,
                    "a normal response", delay.status,
                    note="hooks must be enabled for the overload stimulus to exist")
    )

    # An unrecognised directive must be ignored silently, not rejected. An
    # application that 400s here would fail scenarios for the wrong reason.
    bogus = http.get("/api/v1/products?query=hook-probe",
                     headers={"X-Test-Fault": "not-a-real-directive"})
    out.append(
        assert_that("unrecognised X-Test-Fault is ignored silently",
                    bogus.status is not None and bogus.status < 400,
                    "< 400", bogus.status)
    )

    # Observation paths must be answerable; the fault-time requirement is
    # asserted inside the scenarios that inject faults.
    for path in ("/health/live", "/health/ready"):
        resp = http.get(path)
        out.append(
            assert_that(f"{path} answers", resp.status is not None,
                        "a response", resp.status if resp.status else resp.error)
        )

    exercisable["ASR-P1"] = schema_ok and reset_ok
    exercisable["ASR-P2"] = schema_ok and hooks_ok
    exercisable["ASR-A1"] = schema_ok and reset_ok
    exercisable["ASR-A2"] = schema_ok and reset_ok and hooks_ok
    exercisable["ASR-A3"] = reset_ok
    exercisable["ASR-A4"] = hooks_ok

    out.append(
        assert_that(
            "all six scenarios are exercisable",
            all(exercisable.values()),
            "6 of 6",
            f"{sum(exercisable.values())} of 6",
            note="a scenario that cannot be driven is recorded as not exercisable, not failed",
        )
    )
    return out, exercisable
