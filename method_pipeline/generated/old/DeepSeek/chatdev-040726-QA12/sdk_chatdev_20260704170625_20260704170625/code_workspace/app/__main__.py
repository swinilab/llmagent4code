"""Entry point to launch the OMS server with uv run.

For SQLite (local dev), use a single worker to avoid "database is locked" errors.
For PostgreSQL (docker-compose), set WORKERS=4 via environment variable.
"""

from app.main import app
from app.config import settings

if __name__ == "__main__":
    import uvicorn

    # SQLite does not support concurrent writes from multiple workers.
    # Single worker is safe for local development; use PostgreSQL for multi-worker.
    workers = settings.WORKERS
    if "sqlite" in settings.DATABASE_URL.lower() and workers > 1:
        workers = 1

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=workers,
        log_level=settings.LOG_LEVEL.lower(),
    )