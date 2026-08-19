# Order Management System (OMS)

A production-grade, backend-only e-commerce Order Management System.

## Quick Start

```bash
cd oms-backend
uv sync
uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Documentation

- [ADR and NFR Traceability](docs/adr-and-nfr-traceability.md)
- [Data Architecture](docs/data-architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [OpenAPI Spec](docs/openapi.yaml)

## API Manifests

- [Create APIs](create_apis.json) - Entity creation endpoints
- [Workflow APIs](workflow_apis.json) - State-changing workflow steps
- [NFR Trace](nfr-trace.json) - NFR implementation traceability

## Verification

Run the NFR verification suite:

```bash
bash verification/run_all.sh
```

Individual tests:
- `verification/verify_nfr_1_1.py` - Rate Limiting
- `verification/verify_nfr_1_2.py` - Multiple Data Copies
- `verification/verify_nfr_2_1.py` - Timeout Detection
- `verification/verify_nfr_2_2.py` - Graceful Degradation
- `verification/verify_nfr_2_3.py` - State Resynchronization
- `verification/verify_nfr_2_4.py` - Transactions

## Project Structure

```
oms-backend/
├── src/
│   ├── main.py              # FastAPI application
│   ├── models/              # Pydantic models
│   │   ├── customer.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── payment.py
│   │   └── invoice.py
│   ├── repositories/        # Data access layer
│   │   └── repositories.py
│   ├── services/            # Business logic layer
│   │   └── services.py
│   ├── controllers/         # (integrated in main.py)
│   └── config/              # Configuration
├── verification/            # NFR verification scripts
│   ├── run_all.sh
│   ├── verify_nfr_1_1.py
│   ├── verify_nfr_1_2.py
│   ├── verify_nfr_2_1.py
│   ├── verify_nfr_2_2.py
│   ├── verify_nfr_2_3.py
│   └── verify_nfr_2_4.py
├── docs/                    # Documentation
│   ├── adr-and-nfr-traceability.md
│   ├── data-architecture.md
│   ├── deployment-guide.md
│   └── openapi.yaml
├── infrastructure/          # IaC
│   ├── Dockerfile
│   └── docker-compose.yml
├── create_apis.json         # API manifest
├── workflow_apis.json       # Workflow manifest
├── nfr-trace.json           # NFR traceability
├── start_command.txt        # Start command
└── pyproject.toml           # Project config
```
