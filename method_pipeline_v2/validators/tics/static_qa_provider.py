"""
static_qa_provider.py
─────────────────────
Feeds TICS the real S(x,f) produced by stage 3, replacing the trace-only
fallback that pins every confidence to 1.0.

The join needs no translation: stage 3 already emits function references in the
`path/to/file.py::Class.method` form TICS addresses nodes by, and carries the
NFR label the trace used. Only the shape of the report is coupled here, so a
change to how stage 3 computes score1 is picked up with no edit — which is the
whole reason TICS depends on an interface rather than calling into it.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

from validators.tics.contract import (
    ITacticBindingProvider,
    TacticBinding,
    normalize_function_ref,
    normalize_nfr_id,
)


class StaticQABindingProvider(ITacticBindingProvider):
    """Reads bindings from a stage 3 report.

    `report_path` pins a specific run — the reproducible option, and the one to
    use when re-deriving a published number. Left unset, the newest report in
    `report_dir` is used, which is only safe when stage 3 has just run against
    this same repository; the mismatch guard below catches the case where it did
    not.
    """

    def __init__(
        self,
        report_path: str | Path | None = None,
        report_dir: str | Path = "reports/",
        pattern: str = "**/static_qa_report*.json",
    ) -> None:
        self._report_path = Path(report_path) if report_path else None
        self._report_dir = Path(report_dir)
        self._pattern = pattern

    def bindings(self, repo_root: Path) -> list[TacticBinding]:
        payload = json.loads(self._resolve_report().read_text(encoding="utf-8"))

        reported = payload.get("repo_root")
        if reported and Path(reported).resolve() != Path(repo_root).resolve():
            # Scoring one repository's structure against another's confidences
            # would produce a plausible number built from two different runs.
            raise ValueError(
                f"stage 3 report is for {reported}, not {repo_root}; "
                "run stage 3 against this repository or pass report_path explicitly"
            )

        out: list[TacticBinding] = []
        for entry in payload.get("results", []):
            nfr_id = normalize_nfr_id(entry.get("nfr", ""))
            if nfr_id is None:
                continue
            for function in entry.get("functions", []):
                ref = function.get("ref")
                if not ref:
                    continue
                # A claim stage 3 could not verify arrives as 0.0 and is kept, not
                # dropped: TICS needs it to report coverage honestly.
                score = function.get("score1")
                out.append(
                    TacticBinding(
                        nfr_id=nfr_id,
                        function_ref=normalize_function_ref(ref),
                        s=float(score) if score is not None else 0.0,
                        evidence={
                            "status": function.get("status"),
                            "librariesUsed": function.get("libraries_used", []),
                            "usesAny": function.get("uses_any"),
                        },
                    )
                )
        if not out:
            raise ValueError("stage 3 report contained no usable function bindings")
        return out

    def _resolve_report(self) -> Path:
        if self._report_path:
            if not self._report_path.is_file():
                raise FileNotFoundError(f"stage 3 report not found: {self._report_path}")
            return self._report_path
        candidates = sorted(
            glob.glob(str(self._report_dir / self._pattern), recursive=True),
            key=os.path.getmtime,
        )
        if not candidates:
            raise FileNotFoundError(
                f"no stage 3 report matching {self._pattern} in {self._report_dir}"
            )
        return Path(candidates[-1])
