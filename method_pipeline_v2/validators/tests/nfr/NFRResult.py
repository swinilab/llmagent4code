"""
NFR result types
─────────────────
Value objects returned by individual NFR checks (load test, spike test,
fault injection, etc.) before they get folded into the pipeline's shared
ValidationResult (see interfaces/base.py).

Design note: we deliberately do NOT introduce a parallel "NFRReport" class
that competes with ValidationResult. Instead, each NFR check produces one
NFRCheckResult, and NFRValidator.validate() aggregates a list of these into
the details dict of a single ValidationResult(stage="nfr", ...). This keeps
every stage in the waterfall (1-4) speaking the same contract that
main.py / report_writer already understand.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NFRCheckResult:
    """
    Result of a single NFR check (e.g. NFR 1.1, NFR 2.2).

    One NFRValidator.validate() call typically produces several of these
    (one per NFR id under test), which are then merged into
    ValidationResult.details["checks"].
    """
    nfr_id: str                        # e.g. "NFR 1.1 Response Time"
    passed: bool
    measured: dict[str, Any]           # actual observed values, e.g. {"p95_ms": 180}
    threshold: dict[str, Any] = field(default_factory=dict)  # e.g. {"p95_ms": 200}
    message: str = ""                  # human-readable explanation, esp. on failure

    def to_dict(self) -> dict[str, Any]:
        return {
            "nfr_id": self.nfr_id,
            "passed": self.passed,
            "measured": self.measured,
            "threshold": self.threshold,
            "message": self.message,
        }


def build_validation_result(checks: list[NFRCheckResult]):
    """
    Fold a list of individual NFR checks into the pipeline's shared
    ValidationResult, so NFRValidator can return exactly what
    run_validation() / report_writer already expect from every other stage.
    """
    from interfaces.base import ValidationResult, Status

    all_passed = all(c.passed for c in checks)
    failed = [c for c in checks if not c.passed]

    if all_passed:
        message = f"all {len(checks)} NFR checks passed"
    else:
        failed_ids = ", ".join(c.nfr_id for c in failed)
        message = f"{len(failed)}/{len(checks)} NFR checks failed: {failed_ids}"

    return ValidationResult(
        stage="nfr",
        status=Status.PASS if all_passed else Status.FAIL,
        message=message,
        details={"checks": [c.to_dict() for c in checks]},
    )