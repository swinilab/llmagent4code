# main.py
import argparse
import sys

# The pipeline prints ✅/❌ markers. On Windows the console defaults to cp1252,
# which cannot encode them, and the run dies with UnicodeEncodeError *after*
# the JSON reports are written but *before* report_writer runs. Force UTF-8 and
# never let an unencodable character abort a run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from pipeline import run_pipeline
from pipeline_factory import build


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SWELAB Empirical Study Pipeline")
    parser.add_argument(
        "--phase",
        choices=["gen", "val", "all"],
        default="all",
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        default=None,
        help=(
            "Validation sub-stage to run in isolation "
            "(1=compilability, 2=functional, 3=static QA, 4=QA, 5=TICS, "
            "6=workflow integration). "
            "Only applies when --phase includes val. "
            "Omit to run the full validation waterfall."
        ),
    )
    parser.add_argument("--config", default="pipeline_config.yaml")
    return parser.parse_args()


def main() -> None:
    args       = _parse_args()
    components = build(config_path=args.config)
    run_pipeline(components, phase=args.phase, stage=args.stage)


if __name__ == "__main__":
    main()