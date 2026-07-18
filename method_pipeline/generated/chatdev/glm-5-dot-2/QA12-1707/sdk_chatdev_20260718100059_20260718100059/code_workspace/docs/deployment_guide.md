# Deployment Guide

This guide covers two deployment methods: local (uv) and Docker. Both produce
a runnable production environment on a local machine.

---

## Method 1: Local Deployment with uv

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Steps

1. **Clone and enter the project:**
   ```bash
   cd code_workspace
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```
   This creates a `.venv/` virtual environment and installs all dependencies
   from `pyproject.toml` / `uv.lock`.

3. **(Optional) Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to adjust database path, queue size, degradation thresholds,
   etc. All variables use the `OMS_` prefix. See `.env.example` for defaults.

4. **Start the server:**
   ```bash
   uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000
   ```
   For development with auto-reload:
   ```bash
   uv run uvicorn oms.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Verify the deployment:**
   ```bash
   # Liveness
   curl http://localhost:8000/health
   # Expected: {"status":"alive","service":"OMS Backend"}

   # Readiness (DB, circuit breakers, queue)
   curl http://localhost:8000/health/ready
   # Expected: {"status":"ready","checks":{"database":"ok",...}}

   # API docs
   open http://localhost:8000/api/docs   # Swagger UI
   ```

6. **Run the test suite:**
   ```bash
   uv run pytest tests/ -v --asyncio-mode=auto
   ```

### Notes

- The SQLite database file (`oms.db`) is created automatically on first startup.
  With the default `OMS_DATABASE_URL=sqlite+aiosqlite:///./oms.db` it lives in the
  working directory; set `OMS_DATABASE_URL=sqlite+aiosqlite:///./data/oms.db` to
  place it inside a `data/` directory (auto-created). WAL mode is enabled automatically.
- To reset the database, delete `oms.db`, `oms.db-wal`, and `oms.db-shm`
  (or `data/oms.db*` when using the `data/` path).
- State recovery runs automatically on startup — any orders left in
  non-terminal states from a previous crash are logged and resumed.

---

## Method 2: Docker Deployment

### Prerequisites

- Docker Engine 24+
- Docker Compose v2+

### Steps

1. **Build and start:**
   ```bash
   docker compose up --build -d
   ```
   This builds the image from `Dockerfile`, starts the container, and maps
   port 8000. The SQLite database is persisted in a Docker volume (`oms-data`).

2. **Verify:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/health/ready
   open http://localhost:8000/api/docs
   ```

3. **View logs:**
   ```bash
   docker compose logs -f oms
   ```

4. **Stop:**
   ```bash
   docker compose down
   ```

5. **Stop and remove data volume (full reset):**
   ```bash
   docker compose down -v
   ```

### Notes

- The Docker container runs a single Uvicorn worker by default. SQLite's
  single-writer model means multi-worker write concurrency would cause lock
  contention. For horizontal scaling, switch to PostgreSQL (see ADR-001).
- The SQLite database is written to `/app/data/oms.db` inside the container,
  which is backed by the `oms-data` named volume mounted at `/app/data`. This
  ensures all data (customers, products, orders, invoices, payments) survives
  `docker compose down` / `up` (NFR 2.3 State Preservation). The `Dockerfile`
  pre-creates `/app/data` and `oms/database.py` ensures the directory exists
  at runtime even when the volume is not mounted.
- The healthcheck in `docker-compose.yml` polls `/health` every 30 seconds.

---

## Production Considerations

| Concern | Current Setting | Scaling Path |
|---------|----------------|--------------|
| Database | SQLite WAL (single file) | Migrate to PostgreSQL + asyncpg |
| Workers | 1 (Docker) / configurable (uv) | Use `--workers N` with PostgreSQL |
| Queue | In-process bounded `asyncio.Queue` | External broker (RabbitMQ / Redis) |
| Authentication | None (per requirements) | Add OAuth2 / JWT middleware |
| TLS | None (plain HTTP) | Reverse proxy (nginx / Caddy) with TLS |