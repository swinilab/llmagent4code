# OrderMan

Backend-only Order Management System implementing a seven-step order workflow
with six prescribed architectural tactics, verified end to end against a live
PostgreSQL instance reached through Toxiproxy.

## Quick start

```bash
docker compose up --build -d
```

That single command is also the content of `start_command.txt`. It starts
PostgreSQL 16, Toxiproxy, the proxy initialization check, and the application.
Database migrations run automatically during application startup - no additional
commands are needed.

Once the stack is healthy:

| URL | Purpose |
|---|---|
| http://localhost:8080/docs | Swagger UI |
| http://localhost:8080/redoc | ReDoc |
| http://localhost:8080/openapi.json | OpenAPI 3.1 document |
| http://localhost:8080/health/live | Liveness |
| http://localhost:8080/health/ready | Readiness |
| http://localhost:8080/internal/metrics | Runtime counters |
| http://localhost:8474 | Toxiproxy control API |

Verify startup:

```bash
curl -s http://localhost:8080/health/ready
curl -s http://localhost:8080/internal/metrics
```

## Architecture at a glance

```
client -> AdmissionControlMiddleware   (ASR-P2: bounded concurrent admission)
       -> TestHookMiddleware           (deterministic stimuli, test hooks only)
       -> routes -> services
                 -> TtlCache           (ASR-P1 maintained copy, ASR-A3 degraded reads)
                 -> run_with_resilience (ASR-A1 timeout, ASR-A2 bounded retry)
                    -> session_scope    (ASR-A4 one atomic transaction)
                       -> PostgreSQL via Toxiproxy
```

Each tactic is implemented once, in its own component, and applied at its natural
scope rather than being attached to the endpoint its scenario happens to name.
Full reasoning, alternatives, and scope decisions are in
[architecture/ADRs.md](architecture/ADRs.md); the mapping from each ASR to
concrete files, functions, and metrics is in
[architecture/tactic-traceability.md](architecture/tactic-traceability.md) and
[nfr-trace.json](nfr-trace.json).

## Configuration

All keys are set in `docker-compose.yml` and echoed as one structured log line at
startup.

| Key | Default | Meaning |
|---|---|---|
| `APP_PORT` | `8080` | HTTP listen port |
| `MAX_IN_FLIGHT_REQUESTS` | `10` | Concurrent admitted business requests (ASR-P2) |
| `DB_OPERATION_TIMEOUT_MS` | `1000` | Per-attempt database time limit (ASR-A1) |
| `DB_MAX_ATTEMPTS` | `3` | Bounded retry attempt limit (ASR-A2) |
| `DB_RETRY_BACKOFF_MS` | `100` | Base backoff between retries (ASR-A2) |
| `CACHE_TTL_SECONDS` | `5` | Maintained-copy freshness window (ASR-P1) |
| `ENABLE_TEST_HOOKS` | `false` | Enables `/internal/test/*` and the test headers |

The deployment in `docker-compose.yml` sets `ENABLE_TEST_HOOKS=true` so the
acceptance scenarios can inject deterministic stimuli.

The application reaches PostgreSQL only through Toxiproxy
(`toxiproxy:8666` -> `db:5432`); it never uses `db:5432` directly.

## Running the tests

The test suite exercises the running stack, because the tactics involve
Toxiproxy, real transactions, and real concurrency that an in-process client
cannot reproduce faithfully. Start the stack first, then:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # Linux/macOS

python -m pytest tests/ -q
```

Override the targets with `ORDERMAN_BASE_URL` and `TOXIPROXY_URL` if needed.

Tests create all of their own data and never depend on preloaded business rows.

## Exercising the ASR scenarios manually

```bash
# ASR-A1 - timeout detection: inject latency far above the per-attempt limit
curl -X POST http://localhost:8474/proxies/postgres/toxics \
  -d '{"name":"lat","type":"latency","stream":"downstream","attributes":{"latency":5000}}'
curl -i http://localhost:8080/api/v1/products/<uncached-id>   # 503/504 DEPENDENCY_TIMEOUT
curl -X DELETE http://localhost:8474/proxies/postgres/toxics/lat

# ASR-A2 - bounded retry with two injected transient faults
curl -i -H 'X-Test-Fault: transient-db-failures=2' \
  http://localhost:8080/api/v1/products/<id>                  # 200 after 3 attempts

# ASR-A3 - graceful degradation: disable the proxy entirely
curl -X POST http://localhost:8474/proxies/postgres -d '{"enabled":false}'
curl -i http://localhost:8080/api/v1/products/<warmed-id>     # 200 from retained copy
curl -i http://localhost:8080/api/v1/products/<unwarmed-id>   # 503 DEPENDENCY_UNAVAILABLE
curl -X POST http://localhost:8474/proxies/postgres -d '{"enabled":true}'

# ASR-A4 - transaction rollback
curl -i -X POST -H 'X-Test-Fault: after-payment-update' \
  http://localhost:8080/api/v1/payments/<id>/verify           # 500 TRANSACTION_FAILED
```

## Regenerating the OpenAPI document

`openapi.json` is exported from the real application object and must never be
hand-edited. Re-run this after any route change:

```bash
python scripts/export_openapi.py
```

## Repository layout

```
README.md                            this file
start_command.txt                    the single startup command
create_apis.json                     entity creation manifest
workflow_apis.json                   workflow operation manifest
nfr-trace.json                       machine-readable tactic traceability
openapi.json                         exported OpenAPI 3.1 contract
Dockerfile                           application image
docker-compose.yml                   app + db + toxiproxy + proxy init
requirements.txt                     pinned direct dependencies
alembic.ini, alembic/                migrations (applied automatically at startup)
toxiproxy/toxiproxy.json             declarative `postgres` proxy definition
architecture/ADRs.md                 one ADR per tactic, with scope decisions
architecture/tactic-traceability.md  human-readable traceability matrix
docs/API_CONTRACT.md                 complete API catalog and scenario matrix
scripts/export_openapi.py            OpenAPI exporter
app/                                 application source
tests/                               functional and ASR acceptance tests
```

## Notes on observability

The observation paths - `/health/live`, `/health/ready`, `/internal/metrics`,
`/internal/admission`, and `/internal/test/reset` - bypass admission control,
never consume an admitted slot, and require no database round-trip. They remain
servable while the system is overloaded or its database is unreachable, which is
what makes a failed scenario diagnosable. `/health/ready` is the sole exception
in content: during an outage it reports `503` rather than pretending readiness,
but it still answers promptly.

Structured JSON log lines are written to stdout for overload rejections, database
timeouts, retry attempts (with attempt number), degraded reads, transaction
rollbacks, and dependency state changes, so any scenario can be diagnosed from
`docker compose logs app` alone.
