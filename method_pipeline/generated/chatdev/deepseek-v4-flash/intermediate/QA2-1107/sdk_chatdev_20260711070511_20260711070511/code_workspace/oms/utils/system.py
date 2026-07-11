"""
Shared system resource monitoring utilities (NFR 2.1, NFR 2.2).

Extracted to a single location to eliminate duplication between
DegradationMiddleware and HealthService.
"""
import logging
import time
from typing import Tuple

logger = logging.getLogger(__name__)

# Cache for CPU delta calculation to avoid blocking the event loop
_cpu_cache: dict = {"prev_total": None, "prev_idle": None, "timestamp": 0.0}


def _read_cpu_stats() -> Tuple[int, int]:
    """Read CPU times from /proc/stat. Returns (total, idle)."""
    with open("/proc/stat", "r") as f:
        parts = f.readline().split()
    values = [int(p) for p in parts[1:] if p.isdigit()]
    if len(values) < 4:
        return 0, 0
    return sum(values), values[3]  # idle is index 3


def get_cpu_percent() -> float:
    """
    Return current CPU usage % using cached deltas.

    Does NOT call time.sleep(), so it is safe for async contexts
    (NFR 2.1 – Graceful Degradation). Uses cumulative deltas from
    the last successful read (up to 5 seconds old) to compute the
    *current* CPU utilization, not the cumulative value since boot.
    """
    global _cpu_cache
    try:
        total, idle = _read_cpu_stats()
    except (FileNotFoundError, IndexError, ValueError, OSError):
        logger.debug("Could not read CPU info from /proc/stat")
        return 0.0

    prev_total = _cpu_cache["prev_total"]
    prev_idle = _cpu_cache["prev_idle"]

    if prev_total is not None:
        total_delta = total - prev_total
        idle_delta = idle - prev_idle
        if total_delta > 0:
            _cpu_cache["prev_total"] = total
            _cpu_cache["prev_idle"] = idle
            _cpu_cache["timestamp"] = time.monotonic()
            return round(100.0 * (1 - idle_delta / total_delta), 1)

    # First call or no previous data – store values and return 0.0
    _cpu_cache["prev_total"] = total
    _cpu_cache["prev_idle"] = idle
    _cpu_cache["timestamp"] = time.monotonic()
    return 0.0


def get_mem_percent() -> float:
    """Read memory usage from /proc/meminfo (Linux) or return 0.0 on error."""
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        mem_total = None
        mem_avail = None
        for line in lines:
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                mem_avail = int(line.split()[1])
        if mem_total and mem_avail and mem_total > 0:
            return round(100.0 * (1 - mem_avail / mem_total), 1)
        return 0.0
    except (FileNotFoundError, IndexError, ValueError):
        logger.debug("Could not read memory info from /proc/meminfo")
        return 0.0


def get_system_load() -> Tuple[float, float]:
    """Return (cpu_percent, mem_percent) in one call."""
    return get_cpu_percent(), get_mem_percent()
