# ADR 001 – Database Choice

**Decision:** Use SQLite for local development and as default relational database, with SQLAlchemy ORM.

**Context (NFRs addressed):**
- **NFR 2.1 Localization of Changes:** SQLAlchemy provides a domain‑driven model layer where each entity is a separate Python class, keeping business logic isolated.
- **NFR 2.2 Interface Stability:** The repository pattern abstracts the underlying storage, allowing future migration to PostgreSQL without changing service or controller contracts.
- **NFR 2.3 Deferred Binding:** Database URL is read from environment variable `DATABASE_URL` at runtime via Pydantic Settings.

**Alternatives considered:**
1. **PostgreSQL** – Rejected for initial local simplicity; would require external DB setup.
2. **NoSQL (MongoDB)** – Rejected because relational integrity (FKs, transactions) is crucial for order lifecycle.

**Consequences:**
- Simplicity and zero‑configuration for developers.
- Not suitable for high‑traffic production; migration path to PostgreSQL is straightforward via SQLAlchemy.
