"""Test-session configuration.

The reference application reads its settings once, at import time, into a frozen
Settings object. Several test modules import parts of it, and whichever imports
first fixes the configuration for the whole session -- so a module setting
DATABASE_URL in its own body is too late if another module imported the app
first, and the second module silently inherits a Postgres URL pointing at a
Toxiproxy host that does not exist outside Docker.

Setting it here removes the ordering dependency: conftest is imported before any
test module, so the SQLite URL is in place no matter which module runs first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "evaluator" / "reference_app"

# Point the reference application at a local file database. The scenarios that
# genuinely need PostgreSQL and Toxiproxy run against the container stack, not
# from pytest.
os.environ["DATABASE_URL"] = f"sqlite:///{(REFERENCE / '_test.db').as_posix()}"
os.environ["ENABLE_TEST_HOOKS"] = "true"

# Ensure every deliberate-defect switch is off: these tests describe correct
# behaviour, and a stray switch left set in the environment would make them fail
# for a reason unrelated to the code under test.
for flag in (
    "DEFECT_NO_SINGLE_FLIGHT",
    "DEFECT_QUEUE_INSTEAD_OF_REJECT",
    "DEFECT_METRICS_NEED_DB",
    "DEFECT_PARTIAL_COMMIT",
    "DEFECT_NO_DEGRADED_CACHE",
    "DEFECT_WRONG_ERROR_CODE",
):
    os.environ.pop(flag, None)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REFERENCE))
