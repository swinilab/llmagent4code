"""Structured stdout logging: one JSON object per line.

The scenarios in the generation contract must be diagnosable from container logs
alone, so each mechanism emits a named event with a UTC timestamp and, where one
applies, the controlled `error.code`.
"""

from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timezone
from typing import Any

_write_lock = threading.Lock()


def log_event(event: str, **fields: Any) -> None:
    line = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    for key, value in fields.items():
        if value is not None:
            line[key] = value
    payload = json.dumps(line, default=str, separators=(",", ":"))
    with _write_lock:
        sys.stdout.write(payload + "\n")
        sys.stdout.flush()
