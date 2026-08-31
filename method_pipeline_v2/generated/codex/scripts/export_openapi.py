from pathlib import Path

import yaml

from app.main import app


def export_openapi() -> None:
    specification = yaml.safe_dump(
        app.openapi(),
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    Path("openapi.yaml").write_text(specification, encoding="utf-8")


if __name__ == "__main__":
    export_openapi()
