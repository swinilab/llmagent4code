#!/usr/bin/env python3
"""
test_scoring_actual.py
──────────────────────
Driver for StaticQualityAttributeValidator.

Location: <root>/validators/tests/scoring/test_scoring_actual.py
Runs the Stage-3 static NFR-trace validator against a generated-code repo,
prints the score1/score2/score3 hierarchy, and dumps the full result as JSON
into ./output/.

The repo must contain:
  - the NFR trace file (default: nfr_matrix.json)
  - every source file the trace's `filesImplemented` entries point at

Usage (from anywhere):
  python validators/tests/scoring/test_scoring_actual.py <repo_dir>
  python validators/tests/scoring/test_scoring_actual.py <repo_dir> --trace nfr_matrix.json
  python validators/tests/scoring/test_scoring_actual.py <repo_dir> --catalog path/to/tactic_catalog.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# this file: <root>/validators/tests/scoring/test_scoring_actual.py
# parents[3] == <root> (method_pipeline_v2) -> on sys.path so
# `validators` and `interfaces` resolve when run directly.
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from validators.StaticQualityAttributeValidator import StaticQualityAttributeValidator  # noqa: E402
from interfaces.base import GenerationResult, Status  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "output"  # .../tests/scoring/output


def build_config(args) -> dict:
    validator_cfg: dict = {"nfr_trace_filename": args.trace}
    if args.catalog:
        validator_cfg["tactic_catalog_path"] = args.catalog
    return {
        "validator": validator_cfg,
        "output": {"report_dir": str(OUTPUT_DIR)},
    }


def print_summary(result) -> None:
    tally = result.details.get("tally", {})
    print("=" * 70)
    print(f"stage   : {result.stage}")
    print(f"status  : {result.status.name}")
    print(f"message : {result.message}")
    print("=" * 70)
    print(f"\noverall_score : {tally.get('overall_score')}")

    print("\nscore3 (per QA):")
    for qa, s3 in (tally.get("score3") or {}).items():
        print(f"  {qa:<14} {s3}")

    print("\nscore2 (per tactic):")
    for tactic, s2 in (tally.get("score2") or {}).items():
        print(f"  {tactic:<40} {s2}")

    print("\nper-NFR:")
    for qa, bucket in (tally.get("qa_groups") or {}).items():
        print(f"  [{qa}] score3={bucket.get('score3')}")
        for nfr in bucket.get("nfrs", []):
            print(f"    {nfr['nfr']:<10} status={nfr['status']:<14} score2={nfr['score2']}")
            for fn in nfr.get("functions", []):
                print(f"        fn {fn['ref']:<45} {fn['status']:<8} s1={fn['score1']}")
            for lib in nfr.get("libraries", []):
                print(f"        lib {lib['lib']:<44} {lib['status']}")


def dump_json(result, repo_root: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"scoring_result_{timestamp}.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(repo_root),
        "stage": result.stage,
        "status": result.status.name,
        "message": result.message,
        "details": result.details,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the static NFR-trace validator against a repo.")
    parser.add_argument("repo_dir", help="Path to the generated-code repo (contains the trace + source files).")
    parser.add_argument("--trace", default="nfr_matrix.json", help="Trace filename inside repo_dir (default: nfr_matrix.json).")
    parser.add_argument("--catalog", default=None, help="Path to tactic_catalog.json (optional; omit to accept any tactic).")
    args = parser.parse_args()

    repo_root = Path(args.repo_dir)
    if not repo_root.is_dir():
        print(f"error: repo_dir is not a directory: {repo_root}", file=sys.stderr)
        return 2

    trace_file = repo_root / args.trace
    if not trace_file.is_file():
        print(f"error: trace file not found: {trace_file}", file=sys.stderr)
        return 2

    gen = GenerationResult(status=Status.PASS, model="driver", code=str(repo_root))
    validator = StaticQualityAttributeValidator(build_config(args))
    result = validator.validate(gen)

    print_summary(result)
    out_path = dump_json(result, repo_root)

    print("\n" + "=" * 70)
    print(f"validator report : {result.details.get('report_path', '')}")
    print(f"driver json dump : {out_path}")
    print("=" * 70)

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())