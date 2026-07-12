"""
OMS Backend — CLI entry point.

Usage:
    python -m oms_backend                      # start via uvicorn
    python -m oms_backend --gunicorn           # start via gunicorn
    python -m oms_backend --worker             # start arq background worker
"""
from __future__ import annotations

import asyncio
import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("oms")


def run_server() -> None:
    import uvicorn
    from oms_backend.core.config import get_settings
    settings = get_settings()
    uvicorn.run(
        "oms_backend.server:app",
        host=settings.app.host,
        port=settings.app.port,
        log_level=settings.app.log_level.lower(),
        reload=settings.app.debug,
        loop="uvloop",
    )


def run_gunicorn() -> None:
    import subprocess
    result = subprocess.run(
        ["gunicorn", "-c", "oms_backend/infra/gunicorn.conf.py", "oms_backend.server:app"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    sys.exit(result.returncode)


def run_worker() -> None:
    from oms_backend.infra.worker import run_worker as _run
    asyncio.run(_run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OMS Backend")
    parser.add_argument("--gunicorn", action="store_true", help="Run with Gunicorn")
    parser.add_argument("--worker",   action="store_true", help="Run Arq background worker")
    args = parser.parse_args()

    if args.worker:
        run_worker()
    elif args.gunicorn:
        run_gunicorn()
    else:
        run_server()
