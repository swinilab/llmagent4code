# Order Management System (OMS) - Architecture Documentation

## Context
This document describes the architecture of a production-grade, backend-only e-commerce Order Management System (OMS) that serves APIs for the complete workflow: customer ordering → payment processing → invoicing → shipping → closure.

## Architectural Decision Records (ADRs)

### ADR 1: FastAPI as Web Framework
- **Decision:** Use FastAPI as the web framework
- **Context:** Addresses NFR 1.1 (Performance), NFR 2.1 (Exception Detection)
- **Alternatives considered:**
  1. Flask - Rejected due to lack of async support and built-in validation
  2. Django REST Framework - Rejected due to heavier weight and complexity for API-only service
- **Consequences:** FastAPI provides async support, automatic validation via Pydantic, and OpenAPI generation, but has a smaller ecosystem than Django.

### ADR 2: SQLAlchemy with Async Support
- **Decision:** Use SQLAlchemy 2.0 with async support and aiosqlite for database
- **Context:** Addresses NFR 2.4 (Transactions), NFR 1.2 (Data Copies)
- **Alternatives considered:**
  1. PostgreSQL with asyncpg - Rejected for local development simplicity
  2. MongoDB - Rejected due to lack of ACID transaction support needed for order processing
- **Consequences:** SQLite provides ACID compliance and simplicity, but may need migration to PostgreSQL for high-concurrency production.

### ADR 3: In-Memory Cache
- **Decision:** Implement singleton in-memory cache with TTL
- **Context:** Addresses NFR 1.2 (Multiple Data Copies)
- **Alternatives considered:**
  1. Redis - Rejected for local deployment simplicity
  2. No caching - Rejected due to performance requirements
- **Consequences:** Simple implementation but data lost on restart; suitable for single-instance deployment.

### ADR 4: Token Bucket Rate Limiter
- **Decision:** Implement token bucket rate limiter per event type
- **Context:** Addresses NFR 1.1 (Limit Event Response)
- **Alternatives considered:**
  1. External rate limiter (nginx) - Rejected for application-level control
  2. No rate limiting - Rejected due to DoS protection requirements
- **Consequences:** Application-level rate limiting provides flexibility but adds complexity.

### ADR 5: Layered Architecture
- **Decision:** Implement Controller-Service-Repository pattern
- **Context:** Addresses all NFRs through separation of concerns
- **Alternatives considered:**
  1. Anemic domain model - Rejected due to lack of encapsulation
  2. CQRS - Rejected due to complexity for this scope
- **Consequences:** Clear separation enables testability and maintainability.

## NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|------------------|---------------------|
| NFR 1.1 Limit Event Response | Token bucket rate limiter | `oms/infrastructure/event/rate_limiter.py` | Check `RateLimiter.is_allowed()` returns False after max events |
| NFR 1.2 Maintain Multiple copies of Data | In-memory cache with TTL | `oms/infrastructure/cache/memory_cache.py` | Verify cache hit on second request via logs |
| NFR 2.1 Exception detection | Custom exception hierarchy + handlers | `oms/infrastructure/exceptions.py` | Trigger validation error, verify 400 response |
| NFR 2.2 Graceful Degradation | Exception handlers returning 503 | `oms/infrastructure/exceptions.py::sqlalchemy_exception_handler` | Simulate DB failure, verify 503 response |
| NFR 2.3 State Resynchronization | Cache invalidation on update | `oms/service/*_service.py` | Update entity, verify cache miss on next get |
| NFR 2.4 Transactions | SQLAlchemy async sessions with commit/rollback | `oms/infrastructure/database.py` | Create order, verify atomic line items insertion |

## Data Architecture

### Database Schema
- **customers:** id, name, address, phone, account_number, bank_name, role, order_history (JSON), created_at
- **products:** id, description, price_amount, price_currency, created_at
- **orders:** id, customer_ref (FK), total_amount, status, created_at, updated_at, invoice_ref (FK)
- **line_items:** id, order_id (FK), product_ref (FK), quantity, unit_price_snapshot
- **payments:** id, order_ref (FK), amount, timestamp, status, method
- **invoices:** id, order_ref (FK), billing_name, billing_address, total_amount, issue_date, due_date, status

### Cache Strategy
- Key format: `{entity_type}:{id}` (e.g., `customer:uuid-here`)
- TTL: 300 seconds (configurable)
- Invalidation: On create/update/delete operations

## API Endpoints

### Customers
- `GET /api/v1/customers` - List all customers
- `GET /api/v1/customers/{id}` - Get customer by ID
- `POST /api/v1/customers` - Create customer
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

### Products
- `GET /api/v1/products` - List all products
- `GET /api/v1/products/{id}` - Get product by ID
- `POST /api/v1/products` - Create product
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

### Orders
- `GET /api/v1/orders` - List all orders
- `GET /api/v1/orders/{id}` - Get order by ID
- `GET /api/v1/orders/customer/{customer_id}` - Get orders by customer
- `GET /api/v1/orders/status/{status}` - Get orders by status
- `POST /api/v1/orders` - Create order
- `PUT /api/v1/orders/{id}/status` - Update order status
- `DELETE /api/v1/orders/{id}` - Delete order

### Payments
- `GET /api/v1/payments` - List all payments
- `GET /api/v1/payments/{id}` - Get payment by ID
- `GET /api/v1/payments/order/{order_id}` - Get payments by order
- `POST /api/v1/payments` - Create payment
- `PUT /api/v1/payments/{id}/verify` - Verify payment
- `DELETE /api/v1/payments/{id}` - Delete payment

### Invoices
- `GET /api/v1/invoices` - List all invoices
- `GET /api/v1/invoices/{id}` - Get invoice by ID
- `GET /api/v1/invoices/order/{order_id}` - Get invoice by order
- `POST /api/v1/invoices` - Create invoice
- `PUT /api/v1/invoices/{id}/status` - Update invoice status
- `DELETE /api/v1/invoices/{id}` - Delete invoice

## Order State Machine

```
PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
   ↓         ↓          ↓
CANCELLED  CANCELLED   CANCELLED
```

## Payment State Machine

```
PENDING → VERIFIED
      → REJECTED
```

## Invoice State Machine

```
ISSUED → PAID
      → OVERDUE → PAID
      → CANCELLED
```
