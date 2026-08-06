# Order Management System (OMS) - Architecture Documentation

## Context

This document describes the architecture of the Order Management System (OMS), a production-grade backend-only e-commerce system that serves APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure.

### Roles
- **Customer**: Places orders, makes payments
- **Order Staff**: Reviews/accepts orders, ships orders, closes orders
- **Accountant**: Creates invoices, verifies payments

---

## Architectural Decision Records (ADRs)

### ADR-001: Database Selection - PostgreSQL

**Decision:** Use PostgreSQL as the primary database

**Context:** 
- NFR 2.4: Transactions - requires ACID compliance
- NFR 1.2: Maintain Multiple copies of Data - requires robust replication
- Need for UUID support, JSON fields for line items
- Production-grade reliability requirements

**Alternatives Considered:**
1. **MongoDB**: Rejected because document databases lack strong ACID transaction guarantees across multiple collections, which is critical for order-payment-invoice consistency.
2. **MySQL**: Considered but PostgreSQL offers better UUID native support, superior JSONB handling for line items, and more advanced concurrency control.

**Consequences:**
- (+) Strong ACID compliance for transactional integrity
- (+) Native UUID type support
- (+) JSONB for flexible line item storage
- (-) Requires PostgreSQL installation and management
- (-) Slightly higher operational complexity than SQLite

---

### ADR-002: Caching Strategy - Redis with In-Memory Fallback

**Decision:** Implement Redis-based caching with in-memory fallback for graceful degradation

**Context:**
- NFR 1.2: Maintain Multiple copies of Data (caching)
- NFR 2.2: Graceful Degradation - maintain critical functions during component failures
- Need for distributed cache in production

**Alternatives Considered:**
1. **In-memory cache only**: Rejected because it doesn't support distributed deployments and loses cache on restart.
2. **Database query optimization only**: Rejected because caching provides significantly better response times for read-heavy operations.

**Consequences:**
- (+) Improved read performance through caching
- (+) Graceful degradation when Redis is unavailable
- (+) Supports distributed deployments
- (-) Additional infrastructure dependency (Redis)
- (-) Cache invalidation complexity

---

### ADR-003: Rate Limiting - Token Bucket with Redis

**Decision:** Implement token bucket rate limiting using Redis

**Context:**
- NFR 1.1: Limit Event Response - process events only up to a set maximum rate
- Need to protect against traffic spikes and abuse
- Support for distributed rate limiting

**Alternatives Considered:**
1. **Fixed window rate limiting**: Rejected because it allows burst traffic at window boundaries.
2. **Application-level rate limiting only**: Rejected because it doesn't work across multiple instances.

**Consequences:**
- (+) Smooth rate limiting without boundary bursts
- (+) Distributed rate limiting across instances
- (+) Configurable limits per endpoint
- (-) Redis dependency for distributed operation
- (-) Slight latency overhead for rate check

---

### ADR-004: Retry Logic - Tenacity with Exponential Backoff

**Decision:** Use Tenacity library for retry logic with exponential backoff

**Context:**
- NFR 2.3: State Resynchronization - retry on transient failures
- NFR 2.2: Graceful Degradation - handle temporary failures gracefully
- Need for robust error handling

**Alternatives Considered:**
1. **Custom retry implementation**: Rejected because it would require more code and testing.
2. **No retry logic**: Rejected because transient failures would cause unnecessary errors.

**Consequences:**
- (+) Proven, well-tested retry library
- (+) Configurable backoff strategies
- (+) Built-in exception handling
- (-) Additional dependency
- (-) Learning curve for team

---

### ADR-005: API Framework - FastAPI

**Decision:** Use FastAPI as the web framework

**Context:**
- Need for automatic OpenAPI documentation
- Python type hints for validation
- Async support for future scalability
- Production performance requirements

**Alternatives Considered:**
1. **Flask**: Rejected because it requires additional extensions for validation and OpenAPI generation.
2. **Django REST Framework**: Rejected because it's heavier and less performant for API-only use cases.

**Consequences:**
- (+) Automatic OpenAPI spec generation
- (+) Built-in request validation with Pydantic
- (+) High performance (Starlette-based)
- (+) Async support ready
- (-) Smaller ecosystem than Django

---

### ADR-006: ORM - SQLAlchemy 2.0

**Decision:** Use SQLAlchemy 2.0 with declarative base

**Context:**
- Need for type-safe database operations
- Connection pooling requirements
- Transaction management for NFR 2.4

**Alternatives Considered:**
1. **Raw SQL**: Rejected due to SQL injection risks and lack of abstraction.
2. **SQLAlchemy Core only**: Rejected because ORM provides better developer experience for complex domain models.

**Consequences:**
- (+) Type-safe queries
- (+) Connection pooling built-in
- (+) Transaction management
- (+) Database abstraction
- (-) Learning curve for complex queries

---

## NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|------------------|---------------------|
| NFR 1.1 Limit Event Response | Token bucket rate limiting with Redis | `oms_backend/utils/rate_limiter.py::RateLimiter.is_allowed` | Send >100 requests/second to any POST endpoint; verify 429 response after limit |
| NFR 1.2 Maintain Multiple copies of Data | Redis caching with in-memory fallback | `oms_backend/utils/cache.py::CacheManager.get/set`, `oms_backend/repository/base.py::BaseRepository.get_by_id` | Check Redis for cache keys after GET request; disable Redis and verify in-memory fallback works |
| NFR 2.1 Exception detection | Structured exception hierarchy with timeout detection | `oms_backend/utils/exceptions.py::OMSException`, `oms_backend/utils/retry.py::execute_with_retry` | Trigger validation error and verify 400; trigger timeout and verify 504 |
| NFR 2.2 Graceful Degradation | Fallback mechanisms when Redis unavailable | `oms_backend/utils/cache.py::CacheManager`, `oms_backend/utils/rate_limiter.py::RateLimiter` | Stop Redis service; verify API continues with in-memory cache and allows requests |
| NFR 2.3 State Resynchronization | Periodic cache-DB sync with retry | `oms_backend/utils/retry.py::synchronize_state`, `oms_backend/repository/base.py::BaseRepository.resynchronize` | Modify DB directly; call resynchronize endpoint; verify cache matches DB |
| NFR 2.4 Transactions | SQLAlchemy transaction management with ACID | `oms_backend/infrastructure/database.py::TransactionManager`, `oms_backend/service/order_service.py::OrderService.create_order` | Create order with invalid product; verify rollback (no partial data); create valid order; verify atomic creation |

---

## Data Architecture

### Database Schema

```sql
-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    account_number VARCHAR(20) NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'CUSTOMER',
    order_history JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description TEXT NOT NULL,
    price_amount NUMERIC(10,2) NOT NULL,
    price_currency VARCHAR(3) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_ref UUID NOT NULL REFERENCES customers(id),
    line_items JSONB NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PLACED',
    invoice_ref UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_ref UUID NOT NULL REFERENCES orders(id),
    amount NUMERIC(10,2) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    method VARCHAR(20) NOT NULL
);

-- Invoices table
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_ref UUID NOT NULL REFERENCES orders(id),
    billing_name VARCHAR(100) NOT NULL,
    billing_address VARCHAR(255) NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    issue_date VARCHAR(10) NOT NULL,
    due_date VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ISSUED'
);
```

### Caching Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI   │────▶│   Redis     │
│             │     │   Server    │     │   Cache     │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  PostgreSQL │
                    │   Database  │
                    └─────────────┘
```

- **Cache-aside pattern**: Check cache first, fallback to database
- **Cache invalidation**: On create/update/delete operations
- **TTL**: 5 minutes default for entity cache

---

## API Endpoints

### Version: v1

| Entity | Create | Get All | Get One | Update | Delete |
|--------|--------|---------|---------|--------|--------|
| Customer | POST /api/v1/customers | GET /api/v1/customers | GET /api/v1/customers/{id} | PUT /api/v1/customers/{id} | DELETE /api/v1/customers/{id} |
| Product | POST /api/v1/products | GET /api/v1/products | GET /api/v1/products/{id} | PUT /api/v1/products/{id} | DELETE /api/v1/products/{id} |
| Order | POST /api/v1/orders | GET /api/v1/orders | GET /api/v1/orders/{id} | - | - |
| Payment | POST /api/v1/payments | GET /api/v1/payments | GET /api/v1/payments/{id} | - | - |
| Invoice | POST /api/v1/invoices | GET /api/v1/invoices | GET /api/v1/invoices/{id} | - | - |

### Order Workflow Endpoints

| Action | Endpoint | Description |
|--------|----------|-------------|
| Accept | POST /api/v1/orders/{id}/accept | Order Staff accepts order |
| Cancel | POST /api/v1/orders/{id}/cancel | Cancel order |
| Verify | POST /api/v1/orders/{id}/verify | Verify order after payment |
| Ship | POST /api/v1/orders/{id}/ship | Ship order |
| Close | POST /api/v1/orders/{id}/close | Close completed order |

### Payment Workflow Endpoints

| Action | Endpoint | Description |
|--------|----------|-------------|
| Verify | POST /api/v1/payments/{id}/verify | Accountant verifies payment |
| Reject | POST /api/v1/payments/{id}/reject | Reject payment |

### Invoice Workflow Endpoints

| Action | Endpoint | Description |
|--------|----------|-------------|
| Mark Paid | POST /api/v1/invoices/{id}/mark-paid | Mark invoice as paid |
| Mark Overdue | POST /api/v1/invoices/{id}/mark-overdue | Mark invoice as overdue |
| Cancel | POST /api/v1/invoices/{id}/cancel | Cancel invoice |

---

## Order Status State Machine

```
PLACED ──▶ ACCEPTED ──▶ INVOICED ──▶ PAID ──▶ VERIFIED ──▶ SHIPPED ──▶ CLOSED
   │            │            │
   │            │            └──────▶ CANCELLED
   │            │
   └────────────└──────▶ CANCELLED
```

## Payment Status State Machine

```
PENDING ──▶ VERIFIED
     │
     └──────▶ REJECTED
```

## Invoice Status State Machine

```
ISSUED ──▶ PAID
    │
    ├──▶ OVERDUE
    │
    └──▶ CANCELLED
```
