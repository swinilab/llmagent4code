# main.py
import argparse
from pipeline import run_pipeline
from pipeline_factory import build


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Empirical Study Pipeline")
    parser.add_argument(
        "--phase",
        choices=["gen", "val", "re", "all"],
        default="all",
    )
    parser.add_argument(
        "--scenario",
        default="all_pass",
        choices=["all_pass", "compile_fail_then_fix", "functional_fail_then_fix",
                 "exceed_repair_limit", "functional_fail_no_fix"],
    )
    parser.add_argument("--config", default="pipeline_config.yaml")
    return parser.parse_args()


def main() -> None:
    args       = _parse_args()
    components = build(config_path=args.config, scenario=args.scenario)
    run_pipeline(components, phase=args.phase)


if __name__ == "__main__":
    main()