"""
WorkflowValidator - integration-level stage.

Stage 2 (FunctionalValidator) is unit-level: each BVA/EP case checks one
field constraint against one create endpoint. This stage checks the part a
per-field suite cannot see - whether the entities compose into the state
machine the prompt's Behavior Workflow describes, across requests.

It scores nothing from stage 2 and stage 2 scores nothing from here; the two
numbers are reported separately on purpose.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from interfaces.base import (
    GenerationResult,
    Status,
    ValidationResult,
    app_run_dir,
    app_label as base_app_label,
)
from validators.tests.workflow_suite import run_workflow_suite

CATEGORIES = ("capability", "happy_path", "precondition")


class WorkflowValidator:
    """Runs the lifecycle integration checks against a running generated app."""

    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        http_config = config.get("validation", {}).get("http", {})
        self._base_url = http_config.get("base_url", "http://localhost:8000")
        self._timeout = http_config.get("timeout_seconds", 10.0)
        self._report_dir = config.get("output", {}).get("report_dir", "reports/")

    def validate(self, generation_result: GenerationResult) -> ValidationResult:
        # code already carries the generated/ prefix (see FunctionalValidator).
        workdir = Path(generation_result.code)
        with open(workdir / "create_apis.json", encoding="utf-8") as f:
            api_paths = {k: v["path"] for k, v in json.load(f).items()
                         if isinstance(v, dict) and v.get("path")}

        workflow_api_paths = None
        manifest = workdir / "workflow_apis.json"
        if manifest.exists():
            with open(manifest, encoding="utf-8") as f:
                workflow_api_paths = json.load(f)

        app_label = base_app_label(generation_result.code)
        run_dir = str(app_run_dir(self._report_dir, "workflow_test",
                                  generation_result.code))

        report = run_workflow_suite(self._base_url, api_paths,
                                    workflow_api_paths, self._timeout)

        summary = []
        for category in CATEGORIES:
            checks = report.by_category(category)
            passed = sum(1 for c in checks if c.result)
            summary.append({
                "category": category,
                "total": len(checks),
                "passed": passed,
                "failed": len(checks) - passed,
                "pass_rate": f"{(passed / len(checks) * 100) if checks else 0:.1f}%",
            })

        total = len(report.checks)
        passed = sum(1 for c in report.checks if c.result)
        failed = total - passed
        status = Status.FAIL if failed else Status.PASS
        message = (
            f"{failed} of {total} workflow check(s) failed "
            f"({passed / total * 100:.1f}% passed)." if failed and total
            else f"All {total} workflow checks passed."
        )

        payload = {
            "stage": "workflow",
            "app": app_label,
            "status": status.name,
            "message": message,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / total * 100) if total else 0:.1f}%",
            "transitions_used": report.transitions,
            "warnings": report.warnings,
            "summary": summary,
            "checks": [c.__dict__ for c in report.checks],
            "calls": report.calls,
        }
        report_path = os.path.join(run_dir, "workflow_test_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        return ValidationResult(
            stage="workflow",
            status=status,
            message=message,
            details={
                "app": app_label,
                "run_dir": run_dir,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": payload["pass_rate"],
                "summary": summary,
                "transitions_used": report.transitions,
                "report_path": report_path,
            },
        )
