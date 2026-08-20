# Context

This repository contains a complete backend-only Order Management System for customer ordering, staff acceptance, accountant invoicing, customer payment, accountant verification, shipping, and closure. It exposes synchronous, versioned REST creation and GET APIs for Customer, Product, Order, Invoice, and Payment. Authentication is intentionally out of scope as required.

# Architecture

The implementation is an asynchronous FastAPI modular monolith backed by PostgreSQL and a disposable Redis secondary projection/event stream. Every module has separate schemas/entities, repository persistence, service business rules, controller mapping, and route definition. State changes and outbox events share one ACID transaction; background event publication is rate-limited; Redis outages degrade cache/events without blocking critical PostgreSQL operations.

- NFR matrix and ADRs: [`docs/architecture.md`](docs/architecture.md)
- Data narrative, relationships, lifecycles, and complete schema: [`docs/data-architecture.md`](docs/data-architecture.md), [`schema.sql`](schema.sql)
- API contract: [`openapi.yaml`](openapi.yaml)
- Local production deployment and NFR observation: [`docs/deployment.md`](docs/deployment.md)

# Tasks

- [x] Establish NFR traceability and ADRs before implementation.
- [x] Implement all five domain models with exact lexical, boundary, enum, UUID, date, and semantic validation.
- [x] Implement repositories, transaction-owning services, thin controllers, and versioned routes.
- [x] Implement the complete seven-step workflow and illegal-state handling.
- [x] Implement transactional outbox, bounded dispatch, cache copies, timeouts, graceful degradation, health, metrics, and state repair.
- [x] Provide OpenAPI, API/NFR manifests, schema/migration, containers, deployment guidance, and automated tests.

# Deliverables

1. **NFR Traceability Matrix:** `docs/architecture.md`.
2. **ADRs:** six major decision records in `docs/architecture.md`.
3. **Machine-readable NFR trace:** `nfr-trace.json`, with six locatable implementations.
4. **Data architecture and schema:** `docs/data-architecture.md`, `schema.sql`, SQLAlchemy models, and Alembic migration.
5. **Shared domain models:** `app/domain/schemas.py`, `validators.py`, and `enums.py`.
6. **Complete backend:** `app/repositories`, `app/services`, `app/controllers`, `app/api/routes`, infrastructure, workers, configuration, and `openapi.yaml`.
7. **API creation manifest:** `create_apis.json`, exactly five synchronous POST collection endpoints.
8. **IaC:** `Dockerfile`, `docker-compose.yml`, and `infrastructure/prometheus.yml`.
9. **Local deployment guide:** `docs/deployment.md`.
10. **NFR verification:** executable tests under `tests/nfr` and observation commands in `docs/deployment.md`.

# Output

Start everything with the one line in [`start_command.txt`](start_command.txt):

```sh
docker compose up --build -d
```

The API is then available at `http://localhost:8000`, interactive documentation at `/docs`, readiness at `/health/ready`, and metrics at `/metrics`. The test suite currently contains 55 passing tests and runs with `python -m pytest` after installing `.[test]`, or through the Docker test target documented above.
