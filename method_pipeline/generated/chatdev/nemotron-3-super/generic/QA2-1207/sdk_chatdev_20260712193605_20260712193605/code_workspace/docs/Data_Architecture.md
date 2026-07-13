# Data Architecture

## Overview
The Order Management System (OMS) uses a relational database to store all business entities. The schema is designed to support the core workflow: customer ordering → payment processing → invoicing → shipping → closure.

## Entity Relationship Diagram (ERD)
*(Note: Since we cannot draw images, we describe the relationships in text.)*

### Tables

#### 1. Users
- id (PK)
- name
- address
- phone
- banking_details
- role (ENUM: customer, order_staff, accountant)
- is_active
- created_at
- updated_at

#### 2. Products
- id (PK)
- description
- base_price (in cents)
- currency (default: USD)
- is_active
- created_at
- updated_at

#### 3. Orders
- id (PK)
- customer_id (FK to Users.id)
- status (ENUM: pending, accepted, invoiced, paid, shipped, closed, cancelled)
- total_amount (in cents)
- invoice_id (FK to Invoices.id, nullable)
- created_at
- updated_at

#### 4. OrderItems
- id (PK)
- order_id (FK to Orders.id)
- product_id (FK to Products.id)
- quantity
- unit_price (in cents)
- total_price (in cents)

#### 5. Payments
- id (PK)
- order_id (FK to Orders.id)
- amount (in cents)
- method (VARCHAR)
- status (ENUM: pending, processing, completed, failed, refunded)
- timestamp

#### 6. Invoices
- id (PK)
- order_id (FK to Orders.id)
- billing_info (TEXT)
- amount (in cents)
- issue_date
- due_date
- status (ENUM: draft, issued, paid, overdue, cancelled)
- created_at
- updated_at

## Relationships
- A User can have many Orders (one-to-many).
- An Order has many OrderItems (one-to-many).
- An Order has one Payment (one-to-one, but we allow multiple payments via separate table; actually, an Order can have many Payments).
- An Order has one Invoice (one-to-one).
- A Product can be in many OrderItems (one-to-many).

## Design Decisions
- **Monetary values stored as integers (cents)** to avoid floating-point precision issues.
- **Enum types** for status fields to ensure data integrity.
- **Timestamps** for audit trails (created_at, updated_at).
- **Soft deletes** are not implemented; instead, we use `is_active` flags for Users and Products.
- **Invoice** is linked to Order to satisfy the requirement for invoice reference in Order.

## Indexing
- Primary keys are indexed automatically.
- Foreign keys are indexed for join performance.
- Additional indexes on frequently queried columns (e.g., Orders.customer_id, Orders.status, OrderItems.order_id).

## Extensibility
- The schema is normalized to 3NF.
- Adding new attributes (e.g., tax, discounts) can be done by adding columns to relevant tables.
- The use of JSON/text fields (e.g., billing_info) allows for flexible storage of unstructured data.

## Security
- Passwords are not stored in this schema; we assume authentication is handled elsewhere (though the requirement says no authentication is required, we still store banking details which should be encrypted in a real system).
- Sensitive data like banking details should be encrypted at rest (not implemented in this simplified version).

## Performance Considerations
- Read replicas can be added for reporting queries.
- Partitioning of Orders table by date can be considered for large volumes.
- Caching layer (e.g., Redis) can be introduced for product catalog.

## Backup and Recovery
- Regular database snapshots (for SQLite, file copy; for PostgreSQL, pg_dump).
- Point-in-time recovery possible with WAL archiving (PostgreSQL).

## Compliance
- The design supports GDPR-like requirements by allowing data deletion (cascading deletes) and data portability (export via API).