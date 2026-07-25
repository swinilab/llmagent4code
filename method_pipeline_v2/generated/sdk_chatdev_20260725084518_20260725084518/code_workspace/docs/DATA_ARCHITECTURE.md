# Data Architecture

## Overview

The OMS uses a layered data architecture with clear separation between:
1. **Domain Models** - Business entities with validation logic
2. **Repository Layer** - Data access abstraction
3. **Database Tables** - SQLAlchemy ORM definitions
4. **Persistence Layer** - Write-Ahead Log for crash recovery

## Schema Design

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐
│  Customer   │       │   Product   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ description │
│ address     │       │ price       │
│ phone       │       └─────────────┘
│ banking     │              │
│ role        │              │
│ orderHistory│              │
└─────────────┘              │
       │                     │
       │                     │
       ▼                     ▼
┌─────────────────────────────────┐
│            Order                │
├─────────────────────────────────┤
│ id (PK)                         │
│ customerRef (FK → Customer)     │
│ lineItems (JSON)                │
│ totalAmount                     │
│ status                          │
│ invoiceRef (FK → Invoice)       │
│ createdAt, updatedAt            │
└─────────────────────────────────┘
       │
       │
       ▼
┌─────────────┐       ┌─────────────┐
│   Invoice   │       │   Payment   │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ orderRef    │       │ orderRef    │
│ billingInfo │       │ amount      │
│ totalAmount │       │ timestamp   │
│ issueDate   │       │ status      │
│ dueDate     │       │ method      │
│ status      │       └─────────────┘
└─────────────┘
```

## Table Definitions

### customers
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY, UUID |
| name | VARCHAR(100) | NOT NULL |
| address | VARCHAR(255) | NOT NULL |
| phone | VARCHAR(15) | NOT NULL |
| banking_account_number | VARCHAR(20) | NOT NULL |
| banking_bank_name | VARCHAR(100) | NOT NULL |
| role | VARCHAR(20) | NOT NULL, DEFAULT 'CUSTOMER' |
| order_history | JSON | DEFAULT [] |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW, ON UPDATE |

### products
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY, UUID |
| description | VARCHAR(500) | NOT NULL |
| price_amount | NUMERIC(10,2) | NOT NULL |
| price_currency | VARCHAR(3) | NOT NULL |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW, ON UPDATE |

### orders
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY, UUID |
| customer_ref | VARCHAR(36) | FOREIGN KEY → customers(id) |
| line_items | JSON | NOT NULL |
| total_amount | NUMERIC(10,2) | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PLACED' |
| invoice_ref | VARCHAR(36) | FOREIGN KEY → invoices(id), NULLABLE |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW, ON UPDATE |

### payments
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY, UUID |
| order_ref | VARCHAR(36) | FOREIGN KEY → orders(id) |
| amount | NUMERIC(10,2) | NOT NULL |
| timestamp | DATETIME | DEFAULT NOW |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' |
| method | VARCHAR(20) | NOT NULL |

### invoices
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY, UUID |
| order_ref | VARCHAR(36) | FOREIGN KEY → orders(id) |
| billing_name | VARCHAR(100) | NOT NULL |
| billing_address | VARCHAR(255) | NOT NULL |
| total_amount | NUMERIC(10,2) | NOT NULL |
| issue_date | VARCHAR(10) | NOT NULL (dd/MM/yyyy) |
| due_date | VARCHAR(10) | NOT NULL (dd/MM/yyyy) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'ISSUED' |
| created_at | DATETIME | DEFAULT NOW |

### wal_entries (Write-Ahead Log)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| operation | TEXT | NOT NULL |
| entity_type | TEXT | NOT NULL |
| entity_id | TEXT | NULLABLE |
| payload | TEXT | NOT NULL (JSON) |
| status | TEXT | DEFAULT 'pending' |
| created_at | TEXT | NOT NULL |
| executed_at | TEXT | NULLABLE |

### state_snapshots
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| entity_type | TEXT | NOT NULL |
| entity_id | TEXT | NOT NULL |
| state | TEXT | NOT NULL (JSON) |
| created_at | TEXT | NOT NULL |

## Data Flow

1. **Request → Controller → Service → Repository → Database**
2. **Database → Repository → Service → Controller → Response**
3. **Async Operations:** Request → Queue → Worker → Service → Repository → Database

## Validation Layers

1. **Pydantic Models** - Request/response validation
2. **Domain Models** - Business rule validation
3. **Service Layer** - Cross-entity validation
4. **Database Constraints** - Referential integrity

## Recovery Mechanism

1. **Before operation:** Log to WAL
2. **Execute operation:** Perform business logic
3. **On success:** Mark WAL entry as executed
4. **On crash:** Replay pending WAL entries on restart
