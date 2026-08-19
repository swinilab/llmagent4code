# Local Deployment Guide

## Prerequisites

- Python 3.12+
- uv package manager (https://docs.astral.sh/uv/)

## Quick Start

### 1. Initialize Environment

```bash
# Navigate to project root
cd code_workspace

# Initialize Python environment (already done)
uv venv --python 3.11

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv sync
```

### 3. Start the Server

```bash
# Using the start command
uv run python -m oms_backend.main

# Or directly
uv run uvicorn oms_backend.server:app --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"1.0.0"}
```

## API Endpoints

### Entity CRUD Operations

| Entity | Create | Read | List |
|--------|--------|------|------|
| Customer | POST /api/v1/customers | GET /api/v1/customers/{id} | GET /api/v1/customers |
| Product | POST /api/v1/products | GET /api/v1/products/{id} | GET /api/v1/products |
| Order | POST /api/v1/orders | GET /api/v1/orders/{id} | GET /api/v1/orders |
| Payment | POST /api/v1/payments | GET /api/v1/payments/{id} | GET /api/v1/payments |
| Invoice | POST /api/v1/invoices | GET /api/v1/invoices/{id} | GET /api/v1/invoices |

### Workflow Operations

| Step | Endpoint | Precondition |
|------|----------|--------------|
| Accept Order | POST /api/v1/orders/{id}/accept | PLACED |
| Create Invoice | POST /api/v1/orders/{id}/invoice | ACCEPTED |
| Mark Paid | POST /api/v1/orders/{id}/mark-paid | INVOICED |
| Verify Payment | POST /api/v1/payments/{id}/verify | PENDING |
| Verify Order | POST /api/v1/orders/{id}/verify | PAID |
| Ship Order | POST /api/v1/orders/{id}/ship | VERIFIED |
| Close Order | POST /api/v1/orders/{id}/close | SHIPPED |

## Running NFR Verification Suite

### Prerequisites
- Server must be running at http://localhost:8000

### Run All Tests

```bash
cd verification
chmod +x run_all_tests.sh
./run_all_tests.sh
```

### Run Individual Tests

```bash
# NFR 1.1 - Rate Limiting
python verification/test_nfr_1_1.py

# NFR 1.2 - Caching
python verification/test_nfr_1_2.py

# NFR 2.1 - Timeout Detection
python verification/test_nfr_2_1.py

# NFR 2.2 - Graceful Degradation
python verification/test_nfr_2_2.py

# NFR 2.3 - State Resynchronization
python verification/test_nfr_2_3.py

# NFR 2.4 - Transactions
python verification/test_nfr_2_4.py
```

### Test Results

Results are saved to `verification/results/` directory:
- `nfr_1_1.json`
- `nfr_1_2.json`
- `nfr_2_1.json`
- `nfr_2_2.json`
- `nfr_2_3.json`
- `nfr_2_4.json`

Each result file contains:
- `passed`: boolean indicating test pass/fail
- `observed`: measured metrics
- `threshold`: expected thresholds
- `tacticUsed`: the architectural tactic being tested

## Configuration

Environment variables can be set via `.env` file:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./oms.db

# Server
HOST=0.0.0.0
PORT=8000

# Rate Limiting (NFR 1.1)
MAX_EVENTS_PER_SECOND=100

# Timeout (NFR 2.1)
DEFAULT_TIMEOUT_SECONDS=30
DB_TIMEOUT_SECONDS=10

# Retry (NFR 2.2)
MAX_RETRIES=3
RETRY_DELAY_SECONDS=1.0

# State Sync (NFR 2.3)
STATE_SYNC_INTERVAL=60

# Fault Injection (Testing)
FAULT_INJECTION_ENABLED=false
FAULT_TYPE=
FAULT_DURATION_MS=5000
```

## Database

The database file `oms.db` is created automatically in the project root on first run.

To reset the database:
```bash
rm oms.db
# Restart the server - database will be recreated
```

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitoring

### NFR Statistics

```bash
curl http://localhost:8000/nfr-stats
```

Returns:
- Rate limiter configuration
- State sync statistics
- Fault injection status

### Health Check

```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Database Lock

If you encounter database lock errors:
```bash
# Stop the server
# Remove the database file
rm oms.db
# Restart the server
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --reinstall
```

## Production Considerations

For production deployment:

1. **Use PostgreSQL** instead of SQLite for better concurrency
2. **Enable HTTPS** with proper certificates
3. **Configure proper logging** (currently minimal)
4. **Set up monitoring** (Prometheus, Grafana)
5. **Use Redis** for distributed caching and rate limiting
6. **Deploy behind reverse proxy** (nginx, traefik)
7. **Enable authentication** (currently disabled per requirements)
