# ADR 002: Database Choice

## Status
Accepted

## Context
We need to select a data storage solution for the OMS. The system must store users, products, orders, payments, and invoices with ACID guarantees for transactions (e.g., order creation, payment processing). The database should support moderate to high read/write loads and be suitable for a production environment.

## Decision
We chose to use SQLAlchemy ORM with SQLite for development and testing, and PostgreSQL for production. The choice of database is abstracted via the DATABASE_URL environment variable, allowing easy switching between different databases.

## Consequences
### Pros
- **SQLAlchemy ORM**: Provides a high-level, Pythonic interface to the database, reducing boilerplate and allowing easy switching between databases.
- **SQLite for development**: Zero-configuration, file-based database that is ideal for local development and testing.
- **PostgreSQL for production**: A robust, open-source relational database with strong ACID compliance, support for complex queries, and proven scalability.
- **Environment-driven configuration**: The same codebase can run against different databases by changing the DATABASE_URL.

### Cons
- **SQLite limitations**: Not suitable for high-concurrency write scenarios (though we mitigate this by using WAL mode and proper connection pooling).
- **Migration overhead**: When changing databases, we must ensure compatibility of SQLAlchemy dialects and data types.

## Alternatives Considered
1. **MongoDB**: A NoSQL document store. Rejected because our data is highly relational and requires ACID transactions for operations like order placement and payment processing.
2. **MySQL**: A viable alternative to PostgreSQL, but we chose PostgreSQL for its advanced features (e.g., JSONB, full-text search) and strict adherence to SQL standards.
3. **Amazon DynamoDB**: A managed NoSQL service. Rejected due to the lack of joins and complex transaction support (though it does support transactions, it is more expensive and less flexible for ad-hoc queries).

## Implications
- The application code remains database-agnostic thanks to SQLAlchemy.
- We will use Alembic for database migrations to manage schema changes.
- For production, we will set up a PostgreSQL instance and configure the connection string accordingly.
- We must consider connection pooling and timeout settings appropriately for the chosen database.