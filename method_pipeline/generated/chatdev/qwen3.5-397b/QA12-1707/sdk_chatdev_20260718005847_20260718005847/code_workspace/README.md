# Order Management System (OMS) - Documentation

## NFR Traceability Matrix

| NFR ID | Requirement | Architectural Mechanism | Module/Component | Verification Method |
|--------|-------------|------------------------|------------------|---------------------|
| NFR 1.1 | Response Time | Async I/O with SQLAlchemy async, connection pooling | `oms/config/database.py`, `oms/services/*` | Measure `/health` endpoint latency under load using `ab` or `wrk` |
| NFR 1.2 | Concurrency & Resource Utilization | Async FastAPI with uvicorn workers, connection pool | `oms/server.py`, `oms/config/database.py` | Monitor CPU/memory with `htop` during concurrent requests |
| NFR 1.3 | Queue Management | Pending order count check in OrderService | `oms/services/order_service.py` | Send 1000+ orders and verify rejection when limit reached |
| NFR 2.1 | Graceful Degradation | ENABLE_DEGRADED_MODE config, queue limits | `oms/config/settings.py`, `oms/services/order_service.py` | Disable non-essential features under load, verify core checkout works |
| NFR 2.2 | Fault Detection and Recovery | Health check endpoint, db.health_check(), try/except blocks | `oms/app.py`, `oms/config/database.py` | Kill DB process and verify automatic reconnection on restart |
| NFR 2.3 | State Preservation | SQLite persistence, transaction rollback/commit | `oms/config/database.py`, all repositories | Kill process mid-transaction, restart and verify data consistency |

---

## Architectural Decision Records (ADRs)

### ADR 001: Async-First Architecture

**Decision:** Use async/await throughout the application with FastAPI and SQLAlchemy async.

**Context:** Addresses NFR 1.1 (Response Time), NFR 1.2 (Concurrency).

**Alternatives Considered:**
1. **Synchronous Flask/Django:** Rejected due to blocking I/O limiting concurrency.
2. **FastAPI with sync SQLAlchemy:** Rejected due to thread pool overhead and potential deadlocks.

**Consequences:** 
- Pro: Better resource utilization, higher throughput under load.
- Con: Steeper learning curve, more complex error handling.

---

### ADR 002: SQLite for Local/Development Deployment

**Decision:** Use SQLite with async driver for local deployment.

**Context:** Addresses NFR 2.3 (State Preservation), simplicity for local deployment.

**Alternatives Considered:**
1. **PostgreSQL:** Rejected for local deployment due to complexity and overhead.
2. **In-memory database:** Rejected due to lack of state preservation.

**Consequences:**
- Pro: Zero configuration, file-based persistence, easy backup.
- Con: Not suitable for high-concurrency production (can be swapped via DATABASE_URL).

---

### ADR 003: Repository Pattern for Data Access

**Decision:** Implement repository pattern separating data access from business logic.

**Context:** Addresses maintainability, testability, and NFR 2.2 (Fault Detection).

**Alternatives Considered:**
1. **Active Record pattern:** Rejected due to tight coupling of logic and data access.
2. **Direct SQLAlchemy in services:** Rejected due to code duplication and harder testing.

**Consequences:**
- Pro: Clear separation of concerns, easier testing, reusable data access logic.
- Con: More files and boilerplate code.

---

### ADR 004: Layered Architecture (Controller-Service-Repository)

**Decision:** Implement three-layer architecture with clear boundaries.

**Context:** Addresses maintainability, NFR 2.1 (Graceful Degradation).

**Alternatives Considered:**
1. **Single-layer monolith:** Rejected due to poor separation of concerns.
2. **Microservices:** Rejected due to complexity for single-team deployment.

**Consequences:**
- Pro: Clear responsibilities, easier to implement cross-cutting concerns.
- Con: More files, potential over-engineering for small projects.

---

### ADR 005: Pydantic for Request/Response Validation

**Decision:** Use Pydantic models for all API request/response validation.

**Context:** Addresses data integrity, automatic OpenAPI documentation.

**Alternatives Considered:**
1. **Manual validation:** Rejected due to error-prone and verbose code.
2. **Marshmallow:** Rejected due to FastAPI's native Pydantic integration.

**Consequences:**
- Pro: Automatic validation, type safety, OpenAPI schema generation.
- Con: Runtime validation overhead (minimal).

---

## Data Architecture

### Entity Relationship Diagram

```
Customer (1) ──────< Order (1) >────── (1) Invoice
                        │
                        ├─────< OrderLineItem >───── Product
                        │
                        └───── (1) Payment
```

### Database Schema

```sql
-- Customers
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    banking_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Products
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Orders
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status VARCHAR(50) DEFAULT 'pending',
    total_amount DECIMAL(10,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    invoice_id INTEGER REFERENCES invoices(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    reviewed_at TIMESTAMP,
    shipped_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Order Line Items
CREATE TABLE order_line_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL
);

-- Invoices
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    order_id INTEGER UNIQUE NOT NULL REFERENCES orders(id),
    billing_name VARCHAR(255) NOT NULL,
    billing_address TEXT,
    subtotal DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    issue_date TIMESTAMP,
    due_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'draft',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Payments
CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    order_id INTEGER UNIQUE NOT NULL REFERENCES orders(id),
    invoice_id INTEGER REFERENCES invoices(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    method VARCHAR(50) DEFAULT 'credit_card',
    status VARCHAR(50) DEFAULT 'pending',
    transaction_id VARCHAR(255),
    notes TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Local Deployment Guide

### Prerequisites

- Python 3.12+
- uv package manager

### Installation

```bash
# Clone or navigate to the project directory
cd code_workspace

# Initialize virtual environment (already done)
uv venv --python 3.11

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (already done)
uv add fastapi uvicorn sqlalchemy pydantic alembic python-multipart httpx
```

### Running the Application

```bash
# Option 1: Using main.py
python main.py

# Option 2: Using uvicorn directly
uv run uvicorn oms.app:app --host 0.0.0.0 --port 8000 --workers 4

# Option 3: Development mode with auto-reload
uv run uvicorn oms.app:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite+aiosqlite:///./oms.db | Database connection string |
| DATABASE_ECHO | false | Enable SQL logging |
| HOST | 0.0.0.0 | Server bind address |
| PORT | 8000 | Server port |
| WORKERS | 4 | Number of worker processes |
| MAX_CONNECTIONS | 100 | Database connection pool size |
| MAX_PENDING_ORDERS | 1000 | Queue management limit |

### Accessing the API

- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Root Endpoint:** http://localhost:8000/

---

## Verification Steps for NFRs

### NFR 1.1 - Response Time

```bash
# Install Apache Benchmark
sudo apt-get install apache2-utils

# Run benchmark on product search (core journey)
ab -n 1000 -c 10 http://localhost:8000/api/v1/products?skip=0&limit=100

# Verify average response time is under 100ms
```

### NFR 1.2 - Concurrency

```bash
# Install wrk
sudo apt-get install wrk

# Run concurrent load test
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/orders

# Monitor system resources
htop
```

### NFR 1.3 - Queue Management

```bash
# Create a script to send 1000+ orders
python -c "
import httpx
for i in range(1050):
    r = httpx.post('http://localhost:8000/api/v1/orders', json={
        'customer_id': 1,
        'line_items': [{'product_id': 1, 'quantity': 1}]
    })
    if r.status_code == 400:
        print(f'Queue limit reached at order {i}')
        break
"
```

### NFR 2.1 - Graceful Degradation

```bash
# Set degraded mode
export ENABLE_DEGRADED_MODE=true
export MAX_PENDING_ORDERS=10

# Run server and verify non-essential features are disabled
# while core checkout remains available
```

### NFR 2.2 - Fault Detection

```bash
# Check health endpoint
curl http://localhost:8000/health

# Simulate failure by stopping database (if using external DB)
# Verify automatic reconnection on restart
```

### NFR 2.3 - State Preservation

```bash
# Create an order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "line_items": [{"product_id": 1, "quantity": 1}]}'

# Kill the server process
kill -9 $(pgrep -f "uvicorn oms.app:app")

# Restart server
python main.py

# Verify order still exists
curl http://localhost:8000/api/v1/orders/1
```

---

## API Usage Examples

### Complete Order Workflow

```bash
# 1. Create Customer
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'

# 2. Create Product
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "base_price": 29.99, "stock_quantity": 100}'

# 3. Customer places order (Step 1)
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "line_items": [{"product_id": 1, "quantity": 2}]}'

# 4. Order Staff reviews & accepts (Step 2)
curl -X POST http://localhost:8000/api/v1/orders/1/review \
  -H "Content-Type: application/json" \
  -d '{"accept": true, "notes": "Approved"}'

# 5. Accountant creates invoice (Step 3)
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{"order_id": 1, "billing_name": "John Doe", "tax_rate": 0.1}'

# 6. Customer pays invoice (Step 4)
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"order_id": 1, "amount": 65.98, "method": "credit_card"}'

# 7. Accountant verifies payment (Step 5)
curl -X POST http://localhost:8000/api/v1/payments/1/verify \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'

# 8. Order Staff ships order (Step 6)
curl -X POST http://localhost:8000/api/v1/orders/1/ship \
  -H "Content-Type: application/json" \
  -d '{"notes": "Shipped via FedEx"}'

# 9. Order Staff closes order (Step 7)
curl -X POST http://localhost:8000/api/v1/orders/1/complete \
  -H "Content-Type: application/json" \
  -d '{"notes": "Delivered successfully"}'
```
