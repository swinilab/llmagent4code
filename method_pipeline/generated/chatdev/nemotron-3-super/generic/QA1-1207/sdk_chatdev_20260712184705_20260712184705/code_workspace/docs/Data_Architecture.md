# Data Architecture

## Overview
The Order Management System (OMS) backend uses a relational database (PostgreSQL) to store persistent entities: Customer, Product, Order, OrderItem, Payment, Invoice. The schema is designed to support the full order lifecycle and reporting needs.

## Entity Relationship Diagram (ERD) Description
- **Customer**: One-to-many with Order (a customer can place many orders).
- **Order**: One-to-many with OrderItem (an order contains many line items); one-to-one with Invoice (optional); one-to-many with Payment (an order can have multiple payment attempts).
- **Product**: One-to-many with OrderItem (a product can appear in many order lines).
- **OrderItem**: Belongs to one Order and one Product.
- **Payment**: Belongs to one Order.
- **Invoice**: Belongs to one Order.

## Data Modeling Decisions
- **Data Types**: Use appropriate SQL types (e.g., Numeric for monetary amounts, String for text, DateTime for timestamps, Enums for status fields).
- **Constraints**: Not-null constraints on essential fields; foreign keys to enforce referential integrity.
- **Indexes**: Primary keys indexed automatically; foreign keys indexed for join performance; additional indexes on frequently queried columns (e.g., order status, customer ID).
- **Audit Fields**: `created_at` and `updated_at` timestamps on all entities for traceability.
- **Extensibility**: Use text fields for JSON-like data (e.g., billing_info, banking_details) to allow flexible schema without migrations; alternatively, could use JSONB columns in PostgreSQL for structured data.

## Caching Layer
- **Product Catalog**: Read-heavy product data is cached in Redis to reduce database load and improve response times. Cache-aside pattern with TTL of 5 minutes.
- **Other Data**: Order, payment, invoice data are typically read-modify-write and thus not cached to avoid inconsistency.

## Async Processing
- Long-running operations (e.g., payment gateway interaction) are offloaded to Celery workers using Redis as the broker. This prevents blocking API threads and improves responsiveness under load.

## Backup and Recovery
- Regular database backups (logical dump or snapshot) are recommended.
- Point-in-time recovery capabilities should be configured for production.

## Data Flow
1. **Customer Places Order**: API receives order details, creates Order and OrderItem records, calculates total.
2. **Order Staff Accepts Order**: Updates order status to ACCEPTED.
3. **Accountant Generates Invoice**: Creates Invoice record linked to order, calculates tax and total.
4. **Customer Pays**: Payment record created with status PROCESSING; asynchronous task processes payment; on success, updates Payment status to COMPLETED, Invoice status to PAID, Order status to PAID.
5. **Order Staff Ships Order**: Updates order status to SHIPPED.
6. **Order Staff Closes Order**: Updates order status to CLOSED.

## Security Considerations
- Sensitive data (banking details, payment transaction IDs) should be encrypted at rest. Currently stored as plain text; in production, use encryption or tokenization.
- Access controls: API endpoints should be protected by role-based access (though authentication is out of scope per requirements, we note that in a real system, roles would enforce permissions).

## Scalability
- Horizontal scaling of API layer via multiple workers.
- Horizontal scaling of Celery workers for async tasks.
- Database read replicas can be introduced for read-heavy reporting queries.
- Caching layer (Redis) can be clustered.
