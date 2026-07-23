# Order Management System (OMS) — Deployment Guide

## Overview

The OMS is a production-grade e-commerce backend serving the complete workflow:
customer ordering → payment processing → invoicing → shipping → closure.

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Server | Python 3.12 + FastAPI (async) | REST endpoints, business logic |
| Database | PostgreSQL 16 | ACID-compliant durable storage |
| Cache | Redis 7 | Cache-aside for hot reads, rate limiting |
| Message Queue | RabbitMQ 3 | Deferrable work, transactional outbox |
| Load Testing | Locust | Performance verification |
| Containerization | Docker + Docker Compose | Local deployment |

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- OR Python 3.12+, PostgreSQL 16+, Redis 7+, RabbitMQ 3+ (for bare-metal)
- At least 8GB RAM available for the stack

## Quick Start (Docker Compose)

```bash
# 1. Clone and enter the project
cd oms

# 2. Start all services
docker compose -f deploy/docker-compose.yml up -d

# 3. Verify health
curl http://localhost:8000/health

# 4. Seed test data
python tests/seed_data.py

# 5. Open API docs
open http://localhost:8000/docs
```

## Bare-Metal Deployment

### 1. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv postgresql redis-server rabbitmq-server

# macOS
brew install python@3.12 postgresql redis rabbitmq
```

### 2. Setup Python Environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Services

```bash
# PostgreSQL
sudo -u postgres createuser oms -P  # password: oms
sudo -u postgres createdb oms -O oms

# Redis (already running on localhost:6379)
# RabbitMQ (already running on localhost:5672)
```

### 4. Run the Application

```bash
# Copy environment
cp .env.example .env

# Initialize database
python -c "import asyncio; from oms.infrastructure.database import init_db; asyncio.run(init_db())"

# Run with uvicorn
uvicorn oms.main:app --host 0.0.0.0 --port 8000 --workers 8 --loop uvloop --http httptools
```

### 5. systemd Service (Production)

```bash
sudo cp deploy/oms.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oms
sudo systemctl start oms
sudo systemctl status oms
```

## Resource Sizing

### Target Hardware
- **CPU:** 16 cores (assumed modern server-class CPU, e.g., AMD EPYC or Intel Xeon)
- **RAM:** 98GB total
- **Disk:** SSD with sufficient IOPS

### Pool Sizing Formulas (NFR 1.2)

**Uvicorn Workers (async):**
```
Workers = CPU_CORES * 0.5 = 16 * 0.5 = 8
```
Async workers handle many concurrent connections per worker via event loop.

**DB Connection Pool (HikariCP-style):**
```
Pool Size = Tn * (Cm - 1) + 1
Where Tn = 8 (workers), Cm = 2 (concurrent DB calls per request)
Pool Size = 8 * (2 - 1) + 1 = 9 → rounded to 20 for headroom
Max Overflow = 10 (burst capacity)
Total Max = 30 connections
```

**Redis Connection Pool:**
```
Pool Size = Workers * 2 = 8 * 2 = 16
```

**Rate Limiter (Token Bucket):**
```
Refill Rate = 5,000 tokens/second (sustained throughput for 5,000 sessions)
Burst = 10,000 tokens (absorb 3x spike over ~2 seconds)
```

**Queue Capacity:**
```
Bounded queue = 10,000 messages
Rejection policy = drop oldest (or return 429 to client)
```

## API Endpoints

| Method | Path | Description | Criticality |
|--------|------|-------------|-------------|
| POST | /api/v1/customers | Create customer | Core |
| GET | /api/v1/customers | List customers | Core |
| GET | /api/v1/customers/{id} | Get customer | Core |
| POST | /api/v1/products | Create product | Core |
| GET | /api/v1/products | List/search products | Core |
| GET | /api/v1/products/{id} | Get product | Core |
| POST | /api/v1/orders | Create order (Step 1) | Core, Checkout-critical |
| GET | /api/v1/orders | List orders | Core |
| GET | /api/v1/orders/{id} | Get order | Core |
| POST | /api/v1/orders/{id}/accept | Accept order (Step 2) | Core, Back-office |
| POST | /api/v1/orders/{id}/invoice | Invoice order (Step 3) | Core, Back-office |
| POST | /api/v1/orders/{id}/pay | Pay order (Step 4) | Core, Checkout-critical |
| GET | /api/v1/orders/{id}/payment | Verify payment (Step 5) | Core, Back-office |
| POST | /api/v1/orders/{id}/ship | Ship order (Step 6) | Core, Back-office |
| POST | /api/v1/orders/{id}/close | Close order (Step 7) | Core, Back-office |
| POST | /api/v1/orders/{id}/cancel | Cancel order | Core |
| GET | /api/v1/recommendations/{id} | Recommendations | Non-essential |
| GET | /health | Full health check | Monitoring |
| GET | /health/ready | Readiness probe | Monitoring |
| GET | /health/live | Liveness probe | Monitoring |
| GET | /metrics | Internal metrics | Monitoring |

## Performance Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/locustfile.py --host http://localhost:8000 --users 500 --spawn-rate 10 --run-time 10m

# For sustained test (5,000 sessions)
locust -f tests/locustfile.py --host http://localhost:8000 --users 5000 --spawn-rate 50 --run-time 15m
```

## Reliability Testing

```bash
# Run all reliability tests
python tests/test_reliability.py
```

## Monitoring

- **Health:** GET /health (DB, Redis, RabbitMQ status)
- **Metrics:** GET /metrics (rate limiter state, circuit breaker metrics)
- **Logs:** Structured JSON logs to stdout
- **OpenAPI:** GET /docs (Swagger UI) or /redoc (ReDoc)

## Order State Machine

```
CREATED → ACCEPTED → INVOICED → PAID → SHIPPED → CLOSED
    ↓         ↓          ↓
  CANCELLED (terminal exception state from CREATED, ACCEPTED, INVOICED)
```

All transitions are persisted synchronously (DB write before response).
