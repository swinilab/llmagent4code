"""Export the OpenAPI document from the real application object.

Importing the live `app` guarantees the exported file cannot drift from the
running routes. Re-run this after any route change:

    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.main import app  # noqa: E402  - import after sys.path setup

OUTPUT_PATH = os.path.join(PROJECT_ROOT, "openapi.json")


def main() -> None:
    document = app.openapi()
    document["openapi"] = "3.1.0"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {OUTPUT_PATH} with {len(document.get('paths', {}))} paths")


if __name__ == "__main__":
    main()
