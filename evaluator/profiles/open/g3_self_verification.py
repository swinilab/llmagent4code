"""G3 (open profile) -- auditing the agent's own NFR verification suite.

The open prompt states each NFR as a tactic definition and leaves the mechanism,
the thresholds and the verification approach to the agent. The evaluator
therefore cannot compare a measurement against a number it never specified.
What it can do is audit the evidence the agent was required to produce, and the
audit is where nearly all the discriminating power of this profile lives.

The suite is required to emit, per NFR, a JSON result declaring the fault it
induced, a healthy-condition baseline, the values it observed, the thresholds it
chose, and a verdict. Five things are then checked, ordered by how cheaply a
dishonest suite defeats them:

  1. the verdict is arithmetic, not assertion -- recomputed from observed vs
     threshold rather than trusted;
  2. every threshold names a metric that was actually observed;
  3. the fault was confirmed from outside the application, not assumed;
  4. the baseline differs from the observation, so the fault demonstrably
     reached the system;
  5. the script fails when it should -- a suite whose assertions hold with the
     mechanism disabled has verified nothing.

Point 5 cannot be established from the result files alone; it needs the
mutation probe in `falsifiability.py`. The rest are decidable here, which makes
this gate the automated core and leaves a narrow, well-anchored remainder for
human or model-assisted review.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...report.schema import Assertion, Evidence, GateResult, assert_that

RESULTS_DIRNAME = Path("verification") / "results"

REQUIRED_KEYS = ("nfr", "tacticUsed", "faultInduced", "observed", "threshold", "passed")

# Comparison operators a threshold may declare, and how to apply them.
OPERATORS = {
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "==": lambda a, b: _close(a, b),
    "!=": lambda a, b: not _close(a, b),
}

# Below this relative difference a baseline and an observation are treated as
# indistinguishable, which means the induced fault never reached the mechanism.
# Deliberately loose: the question is whether the system responded at all, not
# whether it responded by a particular margin.
BASELINE_MIN_RELATIVE_CHANGE = 0.10


@dataclass
class ResultAudit:
    """The outcome of auditing one NFR result file."""

    nfr: str
    path: str
    claimed_pass: bool | None = None
    recomputed_pass: bool | None = None
    issues: list[str] = field(default_factory=list)
    observed: dict[str, float] = field(default_factory=dict)
    thresholds: list[dict[str, Any]] = field(default_factory=list)

    @property
    def trustworthy(self) -> bool:
        return not self.issues and self.claimed_pass == self.recomputed_pass


def run(app_dir: Path, expected_nfrs: list[str]) -> GateResult:
    """Audit every declared NFR result under verification/results/."""
    assertions: list[Assertion] = []
    details: dict[str, Any] = {}

    results_dir = app_dir / RESULTS_DIRNAME
    if not results_dir.is_dir():
        return GateResult(
            "G3",
            False,
            [assert_that(
                "verification/results/ exists", False,
                "a directory of per-NFR result files", "absent",
                evidence=Evidence.ARTIFACT,
                note="the verification suite is a required deliverable; without it no "
                     "NFR can be shown to have been exercised",
            )],
            {"results_dir": str(results_dir)},
        )

    audits = [_audit_file(p) for p in sorted(results_dir.glob("*.json"))]
    by_nfr = {a.nfr: a for a in audits if a.nfr}

    # Coverage: every NFR the prompt lists needs a result.
    missing = [n for n in expected_nfrs if not _match(n, by_nfr)]
    assertions.append(
        assert_that(
            "every NFR has a verification result",
            not missing,
            f"{len(expected_nfrs)} results",
            f"missing: {missing}" if missing else "all present",
            evidence=Evidence.ARTIFACT,
        )
    )

    for audit in audits:
        label = audit.nfr or audit.path

        assertions.append(
            assert_that(
                f"{label}: result file is well-formed",
                not audit.issues,
                "all required keys, comparable metrics",
                "; ".join(audit.issues) if audit.issues else "well-formed",
                evidence=Evidence.ARTIFACT,
            )
        )

        # The verdict must follow from the numbers, not merely accompany them.
        if audit.claimed_pass is not None and audit.recomputed_pass is not None:
            assertions.append(
                assert_that(
                    f"{label}: verdict is computed from its measurements",
                    audit.claimed_pass == audit.recomputed_pass,
                    f"passed={audit.recomputed_pass} (recomputed)",
                    f"passed={audit.claimed_pass} (claimed)",
                    evidence=Evidence.ARTIFACT,
                    note="a verdict that disagrees with its own observed/threshold pair "
                         "is either hard-coded or computed from something undisclosed",
                )
            )

    details["audits"] = [
        {
            "nfr": a.nfr,
            "path": a.path,
            "claimed_pass": a.claimed_pass,
            "recomputed_pass": a.recomputed_pass,
            "trustworthy": a.trustworthy,
            "issues": a.issues,
        }
        for a in audits
    ]
    details["audited_count"] = len(audits)

    return GateResult("G3", all(a.passed for a in assertions), assertions, details)


def _audit_file(path: Path) -> ResultAudit:
    audit = ResultAudit(nfr="", path=path.name)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        audit.issues.append(f"unreadable: {str(exc)[:120]}")
        return audit
    if not isinstance(data, dict):
        audit.issues.append("not a JSON object")
        return audit

    audit.nfr = str(data.get("nfr", "")).strip()

    for key in REQUIRED_KEYS:
        if key not in data:
            audit.issues.append(f"missing key {key!r}")

    audit.claimed_pass = bool(data["passed"]) if isinstance(data.get("passed"), bool) else None
    if data.get("passed") is not None and audit.claimed_pass is None:
        audit.issues.append("'passed' must be a boolean")

    audit.observed = _metric_map(data.get("observed"), audit, "observed")
    audit.thresholds = _threshold_list(data.get("threshold"), audit)

    _audit_fault(data.get("faultInduced"), audit)
    _audit_baseline(data.get("baseline"), audit)

    audit.recomputed_pass = _recompute(audit)
    return audit


def _metric_map(raw: Any, audit: ResultAudit, label: str) -> dict[str, float]:
    """Flatten a list of {metric, value} objects into a name->number map."""
    out: dict[str, float] = {}
    if raw is None:
        return out
    if not isinstance(raw, list):
        audit.issues.append(f"'{label}' must be a list of {{metric, value}} objects")
        return out

    for item in raw:
        if not isinstance(item, dict):
            audit.issues.append(f"'{label}' entry is not an object")
            continue
        name = str(item.get("metric", "")).strip()
        value = _number(item.get("value"))
        if not name:
            audit.issues.append(f"'{label}' entry has no metric name")
        elif value is None:
            audit.issues.append(f"'{label}' metric {name!r} has a non-numeric value")
        else:
            out[name] = value
    return out


def _threshold_list(raw: Any, audit: ResultAudit) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        audit.issues.append("'threshold' must be a list of {metric, operator, value}")
        return out

    for item in raw:
        if not isinstance(item, dict):
            audit.issues.append("'threshold' entry is not an object")
            continue
        name = str(item.get("metric", "")).strip()
        operator = str(item.get("operator", "")).strip()
        value = _number(item.get("value"))

        if operator not in OPERATORS:
            audit.issues.append(f"threshold {name!r} uses unsupported operator {operator!r}")
            continue
        if value is None:
            audit.issues.append(f"threshold {name!r} has a non-numeric value")
            continue
        # A threshold on something never measured cannot have been evaluated.
        if name not in audit.observed:
            audit.issues.append(f"threshold {name!r} names a metric absent from 'observed'")
            continue
        out.append({"metric": name, "operator": operator, "value": value})
    return out


def _audit_fault(raw: Any, audit: ResultAudit) -> None:
    """The fault must have been confirmed from outside the application.

    A suite that assumes its fault took effect proves nothing when the fault
    silently failed to apply: every observation then describes a healthy
    system, and the thresholds pass for the wrong reason.
    """
    if raw is None:
        return
    if not isinstance(raw, dict):
        audit.issues.append("'faultInduced' must be an object")
        return
    if not str(raw.get("description", "")).strip():
        audit.issues.append("'faultInduced.description' is empty")
    if raw.get("verified") is not True:
        audit.issues.append(
            "'faultInduced.verified' is not true -- the fault was not confirmed "
            "independently of the application under test"
        )


def _audit_baseline(raw: Any, audit: ResultAudit) -> None:
    """A baseline must differ from the observation it is paired with.

    If the healthy and faulted measurements agree, the induced condition never
    reached the mechanism, whatever the fault injector reported. This catches
    the case `faultInduced.verified` cannot: a proxy correctly disabled, but the
    application reaching its dependency by some other route.
    """
    if raw is None:
        return
    if not isinstance(raw, dict):
        audit.issues.append("'baseline' must be an object with metric and value")
        return

    name = str(raw.get("metric", "")).strip()
    value = _number(raw.get("value"))
    if not name or value is None:
        audit.issues.append("'baseline' needs a metric name and a numeric value")
        return
    if name not in audit.observed:
        audit.issues.append(f"baseline metric {name!r} was not measured under fault")
        return

    observed = audit.observed[name]
    denominator = max(abs(value), abs(observed), 1e-9)
    if abs(observed - value) / denominator < BASELINE_MIN_RELATIVE_CHANGE:
        audit.issues.append(
            f"baseline and observed {name!r} are indistinguishable "
            f"({value} vs {observed}) -- the induced fault did not visibly reach the system"
        )


def _recompute(audit: ResultAudit) -> bool | None:
    """Derive the verdict from observed values and declared thresholds."""
    if not audit.thresholds:
        return None
    return all(
        OPERATORS[t["operator"]](audit.observed[t["metric"]], t["value"])
        for t in audit.thresholds
    )


def _match(nfr: str, by_nfr: dict[str, ResultAudit]) -> bool:
    """Whether a required NFR has a result, matched leniently on its identifier.

    The prompt names NFRs like 'NFR 2.1 Timeout'; a suite may reasonably file
    that as 'nfr-2.1' or 'NFR 2.1'. Matching on the numeric identifier keeps
    the check about coverage rather than about filename style.
    """
    token = _identifier(nfr)
    return any(_identifier(k) == token for k in by_nfr)


def _identifier(label: str) -> str:
    """The 'x.y' identifier inside an NFR label, or the normalised label."""
    for part in label.replace("-", " ").split():
        if part[:1].isdigit() and "." in part:
            return part.strip(".:")
    return label.strip().lower()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if math.isnan(value) or math.isinf(value) else float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
