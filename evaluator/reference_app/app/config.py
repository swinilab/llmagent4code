"""Configuration, plus the deliberate-defect switches used to calibrate.

This application exists to check the evaluator, not to be evaluated. It is
built to satisfy all six scenarios so that a red result from the evaluator can
be attributed to the evaluator rather than to the system under test.

That only establishes the absence of false failures. To also establish that the
evaluator catches real violations, each DEFECT_* flag turns off one mechanism in
a specific, realistic way -- the way a plausible-but-wrong implementation would
get it wrong. With the flag set, the corresponding scenario must go red; if it
stays green, the evaluator is scoring too leniently and the assertion behind it
is not doing its job.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    app_port: int
    max_in_flight_requests: int
    db_operation_timeout_ms: int
    db_max_attempts: int
    db_retry_backoff_ms: int
    cache_ttl_seconds: int
    enable_test_hooks: bool
    database_url: str

    # ── calibration switches (never set in a normal run) ──────────────────
    # Each reproduces one plausible way of getting a tactic wrong.

    # Every concurrent miss issues its own database read. The cache still
    # "works" under light load, so only the 1,000-read phase reveals it.
    defect_no_single_flight: bool
    # Excess requests wait for a slot instead of being refused at once. They
    # still end up rejected, so only the rejection-latency measure catches it.
    defect_queue_instead_of_reject: bool
    # /internal/metrics touches the database, so observability disappears
    # exactly when the outage makes it most necessary.
    defect_metrics_need_db: bool
    # Payment is committed before invoice and order are updated, leaving
    # partial state that only a direct SQL read exposes.
    defect_partial_commit: bool
    # The warmed entry expires normally during an outage, so degraded reads
    # start failing partway through the sixty seconds.
    defect_no_degraded_cache: bool
    # Connection-refused is reported as a timeout, making ASR-A1 and ASR-A3
    # indistinguishable from the outside.
    defect_wrong_error_code: bool

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            app_port=_int("APP_PORT", 8080),
            max_in_flight_requests=_int("MAX_IN_FLIGHT_REQUESTS", 10),
            db_operation_timeout_ms=_int("DB_OPERATION_TIMEOUT_MS", 1000),
            db_max_attempts=_int("DB_MAX_ATTEMPTS", 3),
            db_retry_backoff_ms=_int("DB_RETRY_BACKOFF_MS", 100),
            cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 5),
            enable_test_hooks=_bool("ENABLE_TEST_HOOKS", False),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://orderman:orderman@toxiproxy:8666/orderman",
            ),
            defect_no_single_flight=_bool("DEFECT_NO_SINGLE_FLIGHT"),
            defect_queue_instead_of_reject=_bool("DEFECT_QUEUE_INSTEAD_OF_REJECT"),
            defect_metrics_need_db=_bool("DEFECT_METRICS_NEED_DB"),
            defect_partial_commit=_bool("DEFECT_PARTIAL_COMMIT"),
            defect_no_degraded_cache=_bool("DEFECT_NO_DEGRADED_CACHE"),
            defect_wrong_error_code=_bool("DEFECT_WRONG_ERROR_CODE"),
        )

    def active_defects(self) -> list[str]:
        return [
            name
            for name, on in {
                "no_single_flight": self.defect_no_single_flight,
                "queue_instead_of_reject": self.defect_queue_instead_of_reject,
                "metrics_need_db": self.defect_metrics_need_db,
                "partial_commit": self.defect_partial_commit,
                "no_degraded_cache": self.defect_no_degraded_cache,
                "wrong_error_code": self.defect_wrong_error_code,
            }.items()
            if on
        ]


settings = Settings.load()
