"""
Load-test scenarios configuration.
"""
from __future__ import annotations

# ── Scenario 1: Baseline steady load ───────────────────────────────────────
# 2,000 concurrent virtual users, think time 1–5 s, 10-minute steady state
BASELINE_CONFIG = {
    "users": 2000,
    "spawn_rate": 50,  # users/s
    "run_time": "10m",
    "host": "http://localhost:8000",
    "locustfile": "oms/load_test/locustfile.py",
}

# ── Scenario 2: Sustained load ──────────────────────────────────────────────
# 5,000 concurrent active sessions, ≥10 minutes
SUSTAINED_CONFIG = {
    "users": 5000,
    "spawn_rate": 100,
    "run_time": "10m",
    "host": "http://localhost:8000",
    "locustfile": "oms/load_test/locustfile.py",
}

# ── Scenario 3: 3x spike ───────────────────────────────────────────────────
# Ramp from 0 to 6,000 users over 60 s, hold for ≥5 min
SPIKE_CONFIG = {
    "users": 6000,
    "spawn_rate": 100,  # 100/s → 60 s to reach 6,000
    "run_time": "6m",   # 1 min ramp + 5 min hold
    "host": "http://localhost:8000",
    "locustfile": "oms/load_test/locustfile.py",
}

# ── Pass/Fail Thresholds ────────────────────────────────────────────────────
# NFR 1.1: checkout p95 ≤ 300 ms, p99 ≤ 600 ms; search p95 ≤ 150 ms
# NFR 1.2: 5,000 concurrent sessions, avg queue < 50 ms, CPU 60-85%
# NFR 1.3: no crashes, no OOM, no silent loss under 3x spike
