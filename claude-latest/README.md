# Order Management System — Backend

Production-grade, backend-only OMS covering the full commerce workflow:
**customer ordering → payment processing → invoicing → shipping → closure**,
serving three roles (Customer, Order Staff, Accountant). No authentication, by
design.

Python 3.12 · FastAPI · PostgreSQL 16 (primary + streaming replica) · Redis 7 · Docker Compose

---

## Quick start

```bash
docker compose up --build -d          # == start_command.txt
curl -s localhost:8000/health/ready
```

→ `{"ready":true,"checks":{"primary":"up","replica":"up","redis":"up"}}`

API docs at <http://localhost:8000/docs>. Full guide:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

| Document | Contents |
|---|---|
| [docs/ADR.md](docs/ADR.md) | 6 architectural decision records with alternatives and trade-offs |
| [docs/NFR-TRACEABILITY.md](docs/NFR-TRACEABILITY.md) | NFR → mechanism → module → verification matrix |
| [docs/DATA-ARCHITECTURE.md](docs/DATA-ARCHITECTURE.md) | Data narrative, full schema, state machines |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Local production deployment, configuration, troubleshooting |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | How to observe each NFR, with actual observed output |
| [docs/openapi.json](docs/openapi.json) | Exported OpenAPI 3.1 spec (23 paths) |

Machine-readable deliverables at the project root:
[`create_apis.json`](create_apis.json), [`nfr-trace.json`](nfr-trace.json),
[`start_command.txt`](start_command.txt).

## API

Base path `/api/v1`. Creation endpoints return **201** with the created resource
in the body; `GET /{id}` returns **200** / **404** (absent) / **400** (malformed).

| Entity | Create | Read | Workflow transitions |
|---|---|---|---|
| Customer | `POST /customers` | `GET /customers/{id}` | — |
| Product | `POST /products` | `GET /products/{id}` | — |
| Order | `POST /orders` | `GET /orders/{id}` | `/accept` `/ship` `/close` `/cancel`, `PATCH /status` |
| Invoice | `POST /invoices` | `GET /invoices/{id}` | — |
| Payment | `POST /payments` | `GET /payments/{id}` | `/verify`, `PATCH /verification` |

Operational: `GET /health`, `GET /health/ready`, `GET /ops/nfr`,
`POST /ops/resync`, `POST /ops/degrade/{feature}`, `POST /ops/restore/{feature}`.

### The workflow

```
1. POST /orders                          → PLACED
2. POST /orders/{id}/accept              → ACCEPTED     (Order Staff)
3. POST /invoices                        → INVOICED     (Accountant)
4. POST /payments                        → PAID         (Customer)
5. POST /payments/{id}/verify            → VERIFIED     (Accountant)
6. POST /orders/{id}/ship                → SHIPPED      (Order Staff)
7. POST /orders/{id}/close               → CLOSED       (Order Staff)
```

Illegal transitions answer **409**; nothing ships before payment verification.

### Money is sent as strings

Monetary values cross the API as strings (`"129.99"`) and JSON floats are
rejected. The Field Constraint Table requires exactly 2 decimals with no silent
rounding, and IEEE-754 cannot represent values like `10.005` exactly — see
[ADR-003](docs/ADR.md).

## Non-functional requirements

| NFR | Mechanism |
|---|---|
| 1.1 Limit Event Response | Redis-backed token bucket (atomic Lua), global across workers, 429 + `Retry-After` |
| 1.2 Multiple Copies of Data | Postgres streaming replication **and** read-through Redis cache |
| 2.1 Exception Detection | Structured system-exception handling + timeouts at request/DB/cache layers, circuit breakers |
| 2.2 Graceful Degradation | Critical vs non-critical feature registry; cache and replica outages shed features, never the workflow |
| 2.3 State Resynchronization | 15 s sweep comparing primary/standby lag, row counts and checksums; evicts diverged cache entries |
| 2.4 Transactions | One `unit_of_work()` per workflow step; `SELECT … FOR UPDATE` + optimistic version columns |

Each row is reproducible from [docs/VERIFICATION.md](docs/VERIFICATION.md).

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -q        # 125 tests, requires the stack to be running
```

- `test_workflow.py` — the 7 steps, state-machine guards, cache round-trip
- `test_field_constraints.py` — BVA/EP over every row of the Field Constraint Table
- `test_transactions.py` — atomicity and concurrent-isolation behaviour

## Layout

```
app/
  api/v1/       controllers + versioned routing (customers, products, orders, invoices, payments, ops)
  core/         config, error taxonomy, middleware (rate limit, exception detection)
  domain/       enums + state machines, validators, shared DTOs
  repositories/ SQLAlchemy schema and repositories
  services/     business logic, transaction boundaries, workflow orchestration
  infra/        database engines, cache, rate limiter, degradation, resync
deploy/         replication bootstrap scripts
docs/           ADRs, NFR matrix, data architecture, deployment, verification, OpenAPI
tests/          workflow, field-constraint (BVA/EP) and transaction suites
```
