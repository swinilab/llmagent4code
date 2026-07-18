"""
repairers/report_writer.py
───────────────────────────
Concrete IReportWriter — writes a human-readable report.txt.

The report covers:
  • generation summary
  • validation results (waterfall: shows where it stopped)
  • repair loop history
  • final verdict
"""

from __future__ import annotations

import os
from datetime import datetime

from interfaces.base import (
    GenerationResult,
    IReportWriter,
    RepairResult,
    ValidationResult,
)


class TextReportWriter(IReportWriter):

    def __init__(self, report_path: str = "reports/report.txt") -> None:
        self._path = report_path

    def write(
    self,
    generation:         GenerationResult | None,
    validation_results: list[ValidationResult],
    repair_history:     list[RepairResult],
    all_passed:         bool,
    ) -> str:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

        lines: list[str] = []

        lines.append(f"PIPELINE REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("GENERATION")
        if generation:
            model_name = getattr(generation, 'model', 'N/A')
            output_dir = getattr(generation, 'output_dir', 'N/A')
            
            lines.append(f"model: {model_name}")
            lines.append(f"output: {output_dir}")
            lines.append("")
        else:
            lines.append("Generation failed.")
            lines.append("")


        if validation_results:
            lines.append("VALIDATION")
            for vr in validation_results:
                icon = "✅" if vr.passed else "❌"
                lines.append(f"  {icon} {vr.stage} : {vr.message}")
            lines.append("")

        if repair_history:
            lines.append("REPAIR")
            for rr in repair_history:
                icon = "✅" if rr.all_passed else "❌"
                lines.append(f"  {icon} iteration {rr.iteration}")
                for vr in rr.validation_results:
                    icon = "✅" if vr.passed else "❌"
                    lines.append(f"      {icon} {vr.stage} : {vr.message}")
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
        with open(self._path, "w") as f:
            f.write(report_text)

        return self._path
