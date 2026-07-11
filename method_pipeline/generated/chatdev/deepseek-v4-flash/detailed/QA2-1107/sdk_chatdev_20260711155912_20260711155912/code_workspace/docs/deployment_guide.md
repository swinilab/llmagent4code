# Order Management System — Local Deployment Guide

## Prerequisites

- **Python 3.12+** with `uv` package manager
- **PostgreSQL 16+** running locally or via Docker
- **Docker** (optional, for containerized deployment)
- **systemd** (optional, for Linux service management)

## Quick Start (Local Development)

### 1. Clone and set up the environment

```bash
cd oms
uv venv
source .venv/bin/activate
uv sync
```

### 2. Configure environment

Edit `.env` or set environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=oms
export DB_PASSWORD=oms_secret
export DB_NAME=oms_db
```

### 3. Create the database

```bash
createdb oms_db
# or via psql:
# psql -U postgres -c "CREATE DATABASE oms_db;"
# psql -U postgres -c "CREATE USER oms WITH PASSWORD 'oms_secret';"
# psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE oms_db TO oms;"
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Verify it's running

```bash
curl http://localhost:8000/api/v1/health
# Expected: {"status":"healthy","database":"connected","uptime_seconds":...}
```

## Docker Deployment

### Using Docker Compose (recommended)

```bash
cd deploy
docker-compose up --build
```

This starts both PostgreSQL and the OMS API with proper resource limits:
- OMS API: 2 vCPU, 4 GB RAM
- PostgreSQL: 1 vCPU, 1 GB RAM

### Using Docker directly

```bash
# Build the image
docker build -t oms-api -f deploy/Dockerfile .

# Run with PostgreSQL
docker run -d --name oms-postgres \
  -e POSTGRES_USER=oms \
  -e POSTGRES_PASSWORD=oms_secret \
  -e POSTGRES_DB=oms_db \
  -p 5432:5432 \
  postgres:16-alpine

# Run the API
docker run -d --name oms-api \
  -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e DB_USER=oms \
  -e DB_PASSWORD=oms_secret \
  -e DB_NAME=oms_db \
  --memory=4g --cpus=2 \
  oms-api
```

## systemd Service (Linux)

### 1. Install the service file

```bash
sudo cp deploy/systemd/oms.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Create the application directory

```bash
sudo mkdir -p /opt/oms
sudo cp -r . /opt/oms/
cd /opt/oms
uv venv
source .venv/bin/activate
uv sync
alembic upgrade head
```

### 3. Start the service

```bash
sudo systemctl enable oms
sudo systemctl start oms
sudo systemctl status oms
```

### 4. View logs

```bash
sudo journalctl -u oms -f
```

## API Endpoints

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| GET | `/api/v1/health` | Health check | Core |
| POST | `/api/v1/customers` | Create customer | Core |
| GET | `/api/v1/customers` | List customers | Core |
| GET | `/api/v1/customers/{id}` | Get customer | Core |
| POST | `/api/v1/products` | Create product | Core |
| GET | `/api/v1/products` | List products | Core |
| GET | `/api/v1/products/{id}` | Get product | Core |
| POST | `/api/v1/orders` | Create order (Step 1) | Core |
| GET | `/api/v1/orders` | List orders | Core |
| GET | `/api/v1/orders/{id}` | Get order | Core |
| POST | `/api/v1/orders/{id}/transition` | Transition order (Steps 2-7) | Core |
| POST | `/api/v1/payments` | Process payment (Step 4) | Core |
| GET | `/api/v1/payments/{id}` | Get payment | Core |
| POST | `/api/v1/payments/{id}/verify` | Verify payment (Step 5) | Core |
| POST | `/api/v1/invoices` | Create invoice (Step 3) | Core |
| GET | `/api/v1/invoices/{id}` | Get invoice | Core |
| GET | `/api/v1/recommendations/{id}` | Get recommendations | Non-Essential |

## Workflow Steps

1. **Customer places order**: `POST /api/v1/orders` → status CREATED
2. **Order Staff reviews & accepts**: `POST /api/v1/orders/{id}/transition` with event `review_accept` → ACCEPTED
3. **Accountant creates invoice**: `POST /api/v1/invoices` → INVOICED
4. **Customer pays**: `POST /api/v1/payments` → PAID
5. **Accountant verifies payment**: `POST /api/v1/payments/{id}/verify`
6. **Order Staff ships**: `POST /api/v1/orders/{id}/transition` with event `ship` → SHIPPED
7. **Order Staff closes**: `POST /api/v1/orders/{id}/transition` with event `close` → CLOSED

## Running Tests

### Degradation Test (NFR 2.1)

```bash
# Ensure the API is running
python tests/test_degradation.py
```

### Recovery Test (NFR 2.2)

```bash
# Requires sudo for iptables
sudo python tests/test_recovery.py
```

### State Preservation Test (NFR 2.3)

```bash
# Ensure the API is running
python tests/test_state.py
```

## Resource Limits

The system is designed for a single-node deployment with:
- **CPU**: 2 vCPUs (enforced via Docker `--cpus=2` or systemd `CPUQuota=200%`)
- **RAM**: 4 GB (enforced via Docker `--memory=4g` or systemd `MemoryMax=4G`)
- **DB Pool**: 10 connections (configurable via `DB_POOL_SIZE`)
- **Max concurrent requests**: 100 (configurable via `MAX_CONCURRENT_REQUESTS`)
