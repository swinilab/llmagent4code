# Local Deployment Guide

## Prerequisites

- Docker Engine 24+ with Compose v2 (verified on Docker 28.0.4 / Compose v2.34.0)
- Ports **8000** free on the host
- ~1.5 GB disk for images and volumes

No Python toolchain is needed on the host — everything builds inside containers.

## Start

```bash
docker compose up --build -d
```

That single command is also the content of [`start_command.txt`](../start_command.txt).

First run takes 2–4 minutes: it builds the API image, initializes the primary,
then bootstraps the replica from a `pg_basebackup` of the primary. Compose
health gates order the startup, so the API only starts once all three data
services are healthy.

## Verify it came up

```bash
curl -s localhost:8000/health/ready
# {"ready":true,"checks":{"primary":"up","replica":"up","redis":"up"}}
```

Interactive API docs: <http://localhost:8000/docs>
OpenAPI spec: <http://localhost:8000/openapi.json>

## What is running

| Service | Container | Port | Role |
|---|---|---|---|
| API | `oms-api` | 8000 | FastAPI, 4 uvicorn workers |
| Primary DB | `oms-postgres-primary` | internal | Read/write master |
| Replica DB | `oms-postgres-replica` | internal | Hot standby, streaming replication |
| Redis | `oms-redis` | internal | Cache + shared token bucket |

Only the API is published to the host; the data tier is reachable only on the
`oms-net` bridge network.

## Smoke test the workflow

```bash
# 1. Create a customer and a product
CUST=$(curl -s -X POST localhost:8000/api/v1/customers -H 'Content-Type: application/json' -d '{
  "name":"Alice Smith","address":"12 Elm Street, Springfield","phone":"+14155552671",
  "bankingDetails":{"accountNumber":"12345678","bankName":"Acme Bank"},"role":"CUSTOMER"}' | jq -r .id)

PROD=$(curl -s -X POST localhost:8000/api/v1/products -H 'Content-Type: application/json' -d '{
  "description":"Mechanical keyboard","price":{"amount":"129.99","currency":"USD"}}' | jq -r .id)

# 2. Place -> accept -> invoice -> pay -> verify -> ship -> close
ORDER=$(curl -s -X POST localhost:8000/api/v1/orders -H 'Content-Type: application/json' \
  -d "{\"customerRef\":\"$CUST\",\"lineItems\":[{\"productRef\":\"$PROD\",\"quantity\":3}]}" | jq -r .id)

curl -s -X POST localhost:8000/api/v1/orders/$ORDER/accept | jq -r .status      # ACCEPTED
INV=$(curl -s -X POST localhost:8000/api/v1/invoices -H 'Content-Type: application/json' \
  -d "{\"orderRef\":\"$ORDER\"}" | jq -r .id)
PAY=$(curl -s -X POST localhost:8000/api/v1/payments -H 'Content-Type: application/json' \
  -d "{\"orderRef\":\"$ORDER\",\"amount\":\"389.97\",\"method\":\"CREDIT_CARD\"}" | jq -r .id)
curl -s -X POST localhost:8000/api/v1/payments/$PAY/verify | jq -r .status      # VERIFIED
curl -s -X POST localhost:8000/api/v1/orders/$ORDER/ship  | jq -r .status       # SHIPPED
curl -s -X POST localhost:8000/api/v1/orders/$ORDER/close | jq -r .status       # CLOSED
```

An automated version of the same flow lives in `tests/test_workflow.py`.

## Configuration

Every setting is environment-overridable with the `OMS_` prefix (see
[`app/core/config.py`](../app/core/config.py)); the compose file sets the
production-shaped defaults.

| Variable | Default | Purpose |
|---|---|---|
| `OMS_RATE_LIMIT_CAPACITY` | 100 | Token bucket depth (NFR 1.1) |
| `OMS_RATE_LIMIT_REFILL_PER_SECOND` | 50 | Sustained admitted rate (NFR 1.1) |
| `OMS_CACHE_TTL_SECONDS` | 60 | Entity cache TTL (NFR 1.2) |
| `OMS_DB_STATEMENT_TIMEOUT_MS` | 3000 | Query timeout (NFR 2.1) |
| `OMS_REDIS_TIMEOUT_SECONDS` | 0.25 | Cache call timeout (NFR 2.1) |
| `OMS_BREAKER_FAIL_MAX` | 5 | Failures before a circuit opens (NFR 2.1/2.2) |
| `OMS_RESYNC_INTERVAL_SECONDS` | 15 | Active/standby comparison period (NFR 2.3) |

To run with a tighter limit, for example:

```bash
OMS_RATE_LIMIT_CAPACITY=10 docker compose up -d api
```

## Operations

```bash
docker compose logs -f api          # follow API logs
docker compose ps                   # health of every service
docker compose restart api          # restart just the API
docker compose down                 # stop, keep data volumes
docker compose down -v              # stop and delete all data
```

## Troubleshooting

**Replica never turns healthy.** It bootstraps by streaming a base backup from
the primary and can take ~60 s on first start. Watch it with
`docker compose logs -f postgres-replica`. If it failed permanently, reset just
that node: `docker compose down && docker volume rm oms_replica-data && docker compose up -d`.

**Port 8000 in use.** Change the host side of the mapping in
`docker-compose.yml` (`"8080:8000"`), then `docker compose up -d api`.

**API restarts in a loop.** Almost always the primary is unreachable. Check
`docker compose logs postgres-primary` and confirm `/health/ready` names which
dependency is down.
