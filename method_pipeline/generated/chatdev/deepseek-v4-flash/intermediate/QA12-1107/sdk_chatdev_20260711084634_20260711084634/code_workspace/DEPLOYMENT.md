# OMS Deployment Guide

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Python 3.12+ (for local development)
- PostgreSQL 16 (for local development without Docker)
- Redis 7 (for local development without Docker)

## Quick Start (Docker)

```bash
# 1. Clone the repository
cd oms

# 2. Start all services
docker compose up -d

# 3. Verify the application is running
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# 4. View logs
docker compose logs -f app worker
```

## Local Development Setup

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies (using uv for speed, or pip as fallback)
pip install uv
uv sync
# Alternative: pip install -e .

# 3. Set up environment variables (copy .env.example to .env)
cp .env.example .env
# Edit .env with your local PostgreSQL and Redis connection details

# 4. Initialize the database
psql -U oms -d oms -f init.sql

# 5. Run the application
uvicorn oms.main:app --reload --host 0.0.0.0 --port 8000

# 6. Run the background worker (in a separate terminal)
python -c "from oms.worker import start_worker; import asyncio; asyncio.run(start_worker())"
```

## Configuration

All configuration is via environment variables (see `oms/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://oms:oms@localhost:5432/oms` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `4` | Number of Uvicorn workers |
| `DEBUG` | `false` | Enable debug mode |
| `DB_POOL_SIZE` | `20` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `CB_FAILURE_THRESHOLD` | `5` | Circuit breaker failure threshold |
| `CB_RECOVERY_TIMEOUT` | `30.0` | Circuit breaker recovery timeout (seconds) |
| `MAX_QUEUE_BACKLOG` | `10000` | Maximum queue backlog before admission control |
| `RETRY_ATTEMPTS` | `3` | Retry attempts for transient failures |

## Resource Limits (Target Hardware)

The target hardware class is a single node with:
- Multi-core CPU (8+ cores)
- 98 GB RAM

For local deployment, Docker Compose limits are scaled down:
- PostgreSQL: 2 CPUs, 2 GB RAM
- Redis: 1 CPU, 1 GB RAM
- App: 4 CPUs, 4 GB RAM
- Worker: 2 CPUs, 2 GB RAM

## API Documentation

Once the application is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Health Endpoints

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe (checks DB and Redis)
- `GET /health/circuits` - Circuit breaker states
- `GET /health/queue` - Queue backlog depths

## Running Tests

```bash
# Load tests (requires running application)
python load_test.py

# Reliability tests
python reliability_test.py
```

## Production Considerations

1. **Database**: Use PostgreSQL with replication for high availability.
2. **Redis**: Use Redis Sentinel or Cluster for high availability.
3. **Scaling**: The application is stateless and can be horizontally scaled behind a load balancer.
4. **Monitoring**: Prometheus metrics can be added via the `/metrics` endpoint.
5. **Backup**: Regular PostgreSQL backups and Redis RDB/AOF snapshots.
6. **Security**: Add authentication/authorization for production use.
