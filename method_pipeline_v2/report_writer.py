"""
report_writer.py
─────────────────
Concrete IReportWriter — writes a human-readable report.txt.

The report covers:
  • generation summary
  • validation results (waterfall: shows where it stopped)
  • final verdict
"""

from __future__ import annotations

import os
from datetime import datetime

from interfaces.base import (
    GenerationResult,
    IReportWriter,
    Status,
    ValidationResult,
)


class TextReportWriter(IReportWriter):

    def __init__(self, report_dir: str = "reports/") -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(report_dir, f"report_{timestamp}.txt")

    def write(
        self,
        generation:         GenerationResult | None,
        validation_results: list[ValidationResult],
        all_passed:         bool,
    ) -> str:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

        lines: list[str] = []

        lines.append(f"PIPELINE REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("GENERATION")
        if generation is None:
            lines.append("skipped (phase not run)")
            lines.append("")
        elif generation.status is Status.PASS:
            lines.append(f"model: {generation.model}")
            lines.append(f"code: {generation.code}")
            lines.append("")
        else:
            lines.append("❌ Generation failed.")
            lines.append(f"model: {generation.model}")
            lines.append("")

        if validation_results:
            lines.append("VALIDATION")
            for vr in validation_results:
                icon = "✅" if vr.passed else "❌"
                lines.append(f"  {icon} {vr.stage} : {vr.message}")

                if vr.details.get("stderr"):
                    lines.append(f"    error detail : {vr.details.get('stderr')}")

                summary = vr.details.get("summary")
                if summary:
                    total  = vr.details.get("total")
                    passed = vr.details.get("passed")
                    failed = vr.details.get("failed")
                    lines.append(f"    {failed}/{total} failed ({passed} passed)")
                    for group in summary:
                        lines.append(
                            f"    - {group['group']} : {group['failed']}/{group['total']} failed"
                        )
                    report_path = vr.details.get("report_path")
                    if report_path:
                        lines.append(f"    full report : {report_path}")
                elif vr.details.get("tally"):
                    lines.append(f"    tally : {vr.details.get('tally')}")
                    report_path = vr.details.get("report_path")
                    if report_path:
                        lines.append(f"    full report : {report_path}")
            lines.append("")

        lines.append("RESULT")
        if all_passed:
            lines.append("  ✅ all checks passed — check QA manually")
        else:
            lines.append("  ❌ pipeline failed")
            blocking = next((vr for vr in validation_results if not vr.passed), None)
            if blocking:
                lines.append(f"  blocking stage : {blocking.stage}")
                lines.append(f"  error          : {blocking.message}")

        report_text = "\n".join(lines)
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(report_text)

        return self._path
