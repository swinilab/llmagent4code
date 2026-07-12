# OMS Backend

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                          │
│   /api/v1/customers  /api/v1/orders  /api/v1/invoices   │
│   /api/v1/payments   /api/v1/products /api/v1/health    │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                  Controller Layer                       │
│  CustomerController  OrderController  InvoiceController │
│  PaymentController   ProductController  HealthController│
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                         │
│   CustomerService  OrderService  InvoiceService         │
│   PaymentService   ProductService                       │
│   CircuitBreaker   StateManager   EventBus             │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                Infrastructure Layer                     │
│   SQLAlchemy Repositories  File State Persistence       │
│   Health Checks  Circuit Breaker State                 │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│                     Domain Layer                        │
│   Customer  Order  Product  Payment  Invoice  LineItem  │
└─────────────────────────────────────────────────────────┘
```

## NFR Traceability Matrix

| NFR | Mechanism | Component | Verification |
|-----|-----------|-----------|--------------|
| NFR 2.1 Graceful Degradation | CircuitBreaker + FeatureFlags | resilience.py, services | Disable non-essential features under load, observe core checkout continues |
| NFR 2.2 Fault Detection | HealthCheck + AutoReconnect | health.py, resilience.py | Kill a service thread, observe recovery in health endpoint |
| NFR 2.3 State Preservation | WAL + Snapshots + Idempotency | state_manager.py, repositories | Kill process mid-transaction, observe state restored on restart |

## ADRs

### ADR-001: SQLite with WAL Mode
- **Decision:** Use SQLite with WAL journal mode enabled
- **Context:** NFR 2.3 State Preservation - need ACID compliance and crash recovery
- **Alternatives:** PostgreSQL (overkill for local dev), flat files (no transactions)
- **Consequences:** Limited write concurrency; acceptable for single-instance OMS

### ADR-002: Circuit Breaker Pattern
- **Decision:** Implement circuit breaker for external service calls
- **Context:** NFR 2.1 Graceful Degradation, NFR 2.2 Fault Detection
- **Alternatives:** Simple try-catch (no state), rate limiter (no recovery)
- **Consequences:** Adds latency on state transitions; essential for production

### ADR-003: State Snapshot Pattern
- **Decision:** Periodic state snapshots to disk for crash recovery
- **Context:** NFR 2.3 State Preservation
- **Alternatives:** Full transaction log (complex), database backup (heavy)
- **Consequences:** Small disk overhead; enables fast restart

## Local Deployment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m src.main

# Run tests
pytest tests/ -v
```

## API Documentation

OpenAPI docs available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
- http://localhost:8000/openapi.json (JSON spec)
