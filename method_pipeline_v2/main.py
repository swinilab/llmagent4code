# main.py
import argparse
from pipeline import run_pipeline
from pipeline_factory import build


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SWELAB Empirical Study Pipeline")
    parser.add_argument(
        "--phase",
        choices=["gen", "val", "all"],
        default="all",
    )
    parser.add_argument("--config", default="pipeline_config.yaml")
    return parser.parse_args()


def main() -> None:
    args       = _parse_args()
    components = build(config_path=args.config)
    run_pipeline(components, phase=args.phase)


if __name__ == "__main__":
    main()