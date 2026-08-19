# Data Architecture

## Overview

The OMS backend uses a layered data architecture with the following components:

1. **Domain Models** - SQLAlchemy ORM entities
2. **Schemas** - Pydantic validation schemas
3. **Repositories** - Data access layer
4. **Services** - Business logic layer
5. **Controllers** - REST API layer

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐
│  Customer   │       │   Product   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ description │
│ address     │       │ price_amount│
│ phone       │       │ price_currency│
│ banking_details│    │ created_at  │
│ role        │       │ updated_at  │
│ order_history│      └──────┬──────┘
│ created_at  │              │
│ updated_at  │              │
└──────┬──────┘              │
       │                     │
       │ 1:N                 │ 1:N
       │                     │
       ▼                     ▼
┌─────────────┐       ┌─────────────┐
│    Order    │       │  LineItem   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ productRef  │
│ customerRef │──┐    │ quantity    │
│ line_items  │  │    │ unitPriceSnapshot│
│ total_amount│  │    └─────────────┘
│ status      │  │
│ invoiceRef  │──┼──────┐
│ created_at  │  │      │
│ updated_at  │  │      │
└──────┬──────┘  │      │
       │         │      │
       │ 1:1     │      │ 1:N
       │         │      │
       ▼         │      ▼
┌─────────────┐  │  ┌─────────────┐
│   Invoice   │  │  │   Payment   │
├─────────────┤  │  ├─────────────┤
│ id (PK)     │  │  │ id (PK)     │
│ orderRef    │──┘  │ orderRef    │
│ billing_info│     │ amount      │
│ total_amount│     │ timestamp   │
│ issue_date  │     │ status      │
│ due_date    │     │ method      │
│ status      │     └─────────────┘
└─────────────┘
```

## Schema Definitions

### Customer

```json
{
  "id": "UUIDv4 (server-generated)",
  "name": "string (2-100 chars, regex: ^[\\p{L} .'-]+$)",
  "address": "string (5-255 chars)",
  "phone": "string (8-15 digits, E.164 format)",
  "bankingDetails": {
    "accountNumber": "string (6-20 digits)",
    "bankName": "string (2-100 chars)"
  },
  "role": "enum (CUSTOMER, ORDER_STAFF, ACCOUNTANT)",
  "orderHistory": "array<UUID> (read-only)",
  "createdAt": "datetime (server-generated)",
  "updatedAt": "datetime (server-updated)"
}
```

### Product

```json
{
  "id": "UUIDv4 (server-generated)",
  "description": "string (3-500 chars)",
  "price": {
    "amount": "decimal (0.01-999999.99, exactly 2dp)",
    "currency": "string (USD, VND, EUR)"
  },
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Order

```json
{
  "id": "UUIDv4 (server-generated)",
  "customerRef": "UUID (FK to Customer)",
  "lineItems": [
    {
      "productRef": "UUID (FK to Product)",
      "quantity": "int (1-1000)",
      "unitPriceSnapshot": "decimal (server-computed)"
    }
  ],
  "totalAmount": "decimal (server-computed)",
  "status": "enum (PLACED, ACCEPTED, INVOICED, PAID, VERIFIED, SHIPPED, CLOSED, CANCELLED)",
  "invoiceRef": "UUID (FK to Invoice, nullable)",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Payment

```json
{
  "id": "UUIDv4 (server-generated)",
  "orderRef": "UUID (FK to Order, must be INVOICED)",
  "amount": "decimal (must match invoice total)",
  "timestamp": "datetime (server-generated)",
  "status": "enum (PENDING, VERIFIED, REJECTED)",
  "method": "enum (CREDIT_CARD, BANK_TRANSFER, E_WALLET)"
}
```

### Invoice

```json
{
  "id": "UUIDv4 (server-generated)",
  "orderRef": "UUID (FK to Order, must be ACCEPTED)",
  "billingInfo": {
    "name": "string (snapshot from Customer)",
    "address": "string (snapshot from Customer)"
  },
  "totalAmount": "decimal (must match Order.totalAmount)",
  "issueDate": "date (dd/MM/yyyy format)",
  "dueDate": "date (dd/MM/yyyy, >= issueDate)",
  "status": "enum (ISSUED, PAID, OVERDUE, CANCELLED)"
}
```

## State Machines

### Order Status Flow

```
PLACED → ACCEPTED → INVOICED → PAID → VERIFIED → SHIPPED → CLOSED
   ↓         ↓           ↓
CANCELLED  CANCELLED   CANCELLED
```

### Payment Status Flow

```
PENDING → VERIFIED
     ↓
  REJECTED → PENDING (retry)
```

### Invoice Status Flow

```
ISSUED → PAID
   ↓      ↓
CANCELLED CANCELLED
   ↑
OVERDUE
```

## Validation Rules

All validation rules from the Field Constraint Table are implemented in:

1. **Pydantic Schemas** (`domain/schemas.py`) - Request validation
2. **Model Validators** (`domain/models.py`) - Database-level validation
3. **Service Layer** - Business logic validation (FK existence, state machine)

## Caching Strategy (NFR 1.2)

- **Cache Location:** In-memory dictionary in `Database` class
- **Cache Key Format:** `{entity_type}:{id}` (e.g., `customer:uuid-here`)
- **TTL:** 300 seconds (5 minutes)
- **Invalidation:** On update/delete operations
- **Cache Hit Flow:**
  1. Service method calls `db.get_cached(key)`
  2. If found and not expired, return cached value
  3. If not found, query database and cache result

## Transaction Handling (NFR 2.4)

- **Transaction Boundary:** Service layer methods
- **Commit:** On successful completion
- **Rollback:** On any exception
- **Isolation:** SQLite default (SERIALIZABLE for async)
- **Implementation:** SQLAlchemy async session with context manager

## Data Access Patterns

### Read-Through Cache
```python
async def get_customer(self, customer_id: str):
    cached = db.get_cached(f"customer:{customer_id}")
    if cached:
        return cached
    customer = await repo.get_by_id(customer_id)
    if customer:
        db.set_cached(f"customer:{customer_id}", customer)
    return customer
```

### Transactional Create
```python
async def create_order(self, data: OrderCreate):
    # Validate customer exists
    customer = await customer_repo.get_by_id(data.customerRef)
    if not customer:
        raise ValueError("Customer not found")
    
    # Validate products and compute total
    line_items, total = await self._validate_and_compute(data)
    
    # Create in transaction
    order = await order_repo.create(data, total, line_items)
    
    # Update customer history
    await customer_repo.add_to_order_history(data.customerRef, order.id)
    
    return order
```
