"""OrderMan application factory.

Startup responsibilities, in order:
1. Emit the effective external configuration as one structured log line.
2. Run Alembic migrations to head, so no manual migration command is needed.
3. Register the cross-cutting middleware and all routes.
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import AdmissionControlMiddleware, TestHookMiddleware
from app.api.routes_business import router as business_router
from app.api.routes_ops import router as ops_router
from app.core.config import settings
from app.core.logging import log_event

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATION_MAX_ATTEMPTS = 30
MIGRATION_RETRY_SECONDS = 2


def run_migrations() -> None:
    """Apply Alembic migrations to head as part of startup.

    The database reached through Toxiproxy may not accept connections the instant
    the app starts, so migration is retried on a bounded schedule. This retry is
    startup orchestration, distinct from the request-path retry policy of ASR-A2.
    """
    config = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)

    last_error: Exception | None = None
    for attempt in range(1, MIGRATION_MAX_ATTEMPTS + 1):
        try:
            command.upgrade(config, "head")
            log_event("migrations_applied", attempt=attempt)
            return
        except Exception as exc:  # noqa: BLE001 - reported and retried below
            last_error = exc
            log_event(
                "migration_attempt_failed",
                attempt=attempt,
                max_attempts=MIGRATION_MAX_ATTEMPTS,
                detail=str(exc)[:200],
            )
            time.sleep(MIGRATION_RETRY_SECONDS)

    log_event("migrations_failed", detail=str(last_error)[:500])
    raise RuntimeError(f"Database migrations failed after {MIGRATION_MAX_ATTEMPTS} attempts")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log_event("startup_configuration", **settings.as_log_payload())
    run_migrations()
    log_event("application_started", port=settings.app_port)
    yield
    log_event("application_stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="OrderMan",
        version="1.0.0",
        description=(
            "Backend-only Order Management System implementing a seven-step order "
            "workflow with cached product reads, admission control, database "
            "timeout and retry, graceful degradation, and transactional integrity."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware executes in reverse registration order, so admission control
    # runs first: the test delay must occur *after* admission, while the slot is
    # held, so that an overload client exercises the real admission policy.
    app.add_middleware(TestHookMiddleware)
    app.add_middleware(AdmissionControlMiddleware)

    register_error_handlers(app)
    app.include_router(ops_router)
    app.include_router(business_router)
    return app


app = create_app()
