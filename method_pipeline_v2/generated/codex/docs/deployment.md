# Context

The supported local production topology is API + PostgreSQL + Redis + Prometheus under Docker Compose. PostgreSQL and Redis are private to the Compose network; only the API (`8000`) and Prometheus (`9090`) are published.

# Architecture

The API container runs the Alembic migration before Uvicorn. It then starts the REST service, bounded outbox dispatcher, periodic state synchronizer, health probes, and Prometheus endpoint. Container health and dependency ordering prevent requests before migration/startup completes.

# Tasks

## Start

1. Install Docker Desktop/Engine with Compose v2.
2. Copy `.env.example` to `.env` and replace `POSTGRES_PASSWORD`. Keep the password URL-safe because it is interpolated into `OMS_DATABASE_URL`.
3. From the project root run the single command recorded in `start_command.txt`:

   ```sh
   docker compose up --build -d
   ```

4. Verify `http://localhost:8000/health/live`, `http://localhost:8000/health/ready`, `http://localhost:8000/docs`, and `http://localhost:9090`.

`docker compose down` stops the stack while retaining named volumes. `docker compose down -v` also destroys local PostgreSQL, Redis, and Prometheus data and should be used only when a full reset is intended.

## Test

Run the hermetic test target without external services:

```sh
docker build --target test -t oms-test .
docker run --rm oms-test
```

For a local Python 3.12+ environment:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/python -m pytest
```

On Unix-like systems use `.venv/bin/python` instead. Regenerate the committed OpenAPI spec after route/schema changes with `.venv/Scripts/python scripts/export_openapi.py`.

## Exercise the workflow

Use the Swagger UI at `/docs` or POST in this sequence:

1. `/api/v1/customers`
2. `/api/v1/products`
3. `/api/v1/orders`
4. `/api/v1/orders/{id}/accept`
5. `/api/v1/invoices`
6. `/api/v1/payments`
7. `/api/v1/payments/{id}/verify`
8. `/api/v1/orders/{id}/ship`
9. `/api/v1/orders/{id}/close`

Creation amounts are JSON strings such as `"100.00"`; this preserves the mandated lexical precision.

## Observe each NFR

| NFR | Reproducible observation |
|---|---|
| 1.1 Limit Event Response | Run `pytest tests/nfr/test_nfr_mechanisms.py::test_outbox_dispatch_obeys_configured_maximum_rate`; it enqueues four events at rate two/second and asserts the publish window. In Compose, set `OMS_EVENT_MAX_RATE=2` and watch `oms_outbox_published_total`. |
| 1.2 Multiple Copies | Create/fetch a product, then run `docker compose exec redis redis-cli --scan --pattern "oms:entity:product:*"`; the corresponding PostgreSQL row remains canonical. |
| 2.1 Exception Detection | Run the timeout test or `docker compose stop redis`; `/health/ready` reports Redis `down` and status `degraded` within the configured dependency timeout. |
| 2.2 Graceful Degradation | With Redis stopped, POST/GET domain data still succeeds through PostgreSQL and outbox rows accumulate. Restart with `docker compose start redis`; publication resumes. |
| 2.3 State Resynchronization | Change/delete an `oms:entity:*` Redis key, POST `/internal/resynchronize`, and observe `repaired > 0` plus `oms_resync_mismatches_total`. |
| 2.4 Transactions | Run `pytest tests/nfr/test_nfr_mechanisms.py::test_transaction_rolls_back_domain_and_outbox_together`; the forced failure leaves both domain and outbox counts at zero. |

# Deliverables

- `Dockerfile` with runtime and test targets
- `docker-compose.yml` with persistent stores and health checks
- `infrastructure/prometheus.yml`
- `.env.example`
- `alembic.ini` and migration
- `start_command.txt`

# Output

A successful start serves the API on `http://localhost:8000`. Readiness can be `ready` or `degraded`; it returns HTTP 503 only when the critical PostgreSQL store is unavailable.
