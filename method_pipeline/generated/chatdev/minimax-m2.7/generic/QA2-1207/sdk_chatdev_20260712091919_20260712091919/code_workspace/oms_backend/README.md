"""
Order Management System Backend - README
=========================================

Architecture Overview:
- FastAPI-based REST API backend
- SQLite with SQLAlchemy ORM for persistence
- Layered architecture: Domain -> Infrastructure -> Services -> Controllers -> API

NFR Support:
- NFR 2.1 Graceful Degradation: Circuit breaker + feature flags
- NFR 2.2 Fault Detection: Health checks + automatic reconnection
- NFR 2.3 State Preservation: WAL mode + state snapshots + idempotency keys

Workflow:
1. Customer places order
2. Order Staff reviews & accepts
3. Accountant creates invoice
4. Customer pays invoice
5. Accountant verifies payment
6. Order Staff ships order
7. Order Staff closes order

Roles:
- Customer: place orders, pay invoices
- Order Staff: accept, ship, close orders
- Accountant: create invoices, verify payments
"""

__version__ = "1.0.0"
