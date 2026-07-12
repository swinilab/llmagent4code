"""
Gunicorn configuration for production deployment.

Workers: 2 * CPU_CORES + 1 (maximizes CPU utilization on 98GB RAM machines — NFR 1.2).
Worker type: UvicornWorker (uvloop + asyncpg for high concurrency).
Graceful timeout: 30s (enough to drain in-flight requests — NFR 1.3).
"""
from __future__ import annotations

import multiprocessing
import os

# ── Worker sizing ──────────────────────────────────────────────────────────────

_cpu_count = os.cpu_count() or 4
_workers = 2 * _cpu_count + 1  # e.g., 4 cores → 9 workers

# ── Bind ───────────────────────────────────────────────────────────────────────

bind = os.getenv("OMS_BIND", "0.0.0.0:8000")

# ── Logging ────────────────────────────────────────────────────────────────────

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("OMS_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ── Worker lifecycle (NFR 1.3: graceful shutdown) ───────────────────────────────

worker_class = "uvicorn.workers.UvicornWorker"
graceful_timeout = 30          # seconds to wait for in-flight requests to drain
timeout = 60                   # seconds before a worker is killed if unresponsive
max_requests = 10000           # restart worker after N requests (memory leak prevention)
max_requests_jitter = 1000     # add randomness to avoid all workers restarting at once

# ── Process naming ─────────────────────────────────────────────────────────────

proc_name = "oms-backend"

# ── Preloading ────────────────────────────────────────────────────────────────
# Preload app into master process so all workers share one memory copy (copy-on-write)
preload_app = True

# ── Security ───────────────────────────────────────────────────────────────────

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
