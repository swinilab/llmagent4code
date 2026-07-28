# Data Architecture Narrative & Schema

The OMS stores its data in a relational SQLite database using **SQLAlchemy (async)**. The schema mirrors the domain model defined in the requirements.

## Entity‑Relationship Overview
- **Customer** (1) ── (N) **Order**
- **Order** (1) ── (N) **LineItem**
- **Product** (1) ── (N) **LineItem**
- **Order** (1) ── (0..1) **Invoice**
- **Order** (1) ── (N) **Payment**

## Tables
| Table | Columns (type) |
|-------|----------------|
| customers | id (PK, UUID), name, address, phone, banking_account_number, banking_bank_name, role |
| products | id (PK, UUID), description, price_amount (DECIMAL), price_currency |
| orders | id (PK, UUID), customer_id (FK), status (enum), created_at, updated_at, total_amount, invoice_id (FK) |
| line_items | id (PK, autoinc), order_id (FK), product_id (FK), quantity, unit_price_snapshot |
| invoices | id (PK, UUID), order_id (FK), billing_name, billing_address, total_amount, issue_date, due_date, status |
| payments | id (PK, UUID), order_id (FK), amount, timestamp, status, method |

All **UUID** columns are stored as 36‑character strings. Monetary amounts use **NUMERIC(14,2)** to guarantee two‑decimal‑place precision without rounding.

### Referential Integrity
- Foreign keys enforce existence of referenced rows.
- Application layer validates state transitions (e.g., an Order must be `ACCEPTED` before an Invoice can be created).

### Auditing & Resilience
- Each state‑changing operation appends a record to a **Write‑Ahead Log** (`app/persistence/oms.wal`). On startup the system replays this log to restore pending work, satisfying NFR 2.3.

### Concurrency
- The database is accessed via a single **AsyncEngine** with a connection pool. Tenacity retries transient connection failures.

---
