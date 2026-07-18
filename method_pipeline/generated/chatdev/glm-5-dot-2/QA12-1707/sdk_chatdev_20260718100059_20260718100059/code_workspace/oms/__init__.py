"""
OMS — Order Management System backend package.

A production-grade, backend-only e-commerce OMS built with FastAPI,
SQLAlchemy (async), and SQLite (WAL mode).

Layers:
  - models/      SQLAlchemy ORM models
  - schemas/     Pydantic request/response schemas (shared domain models)
  - repositories/ Data access (generic base + entity-specific)
  - services/    Business logic, transactions, workflow orchestration
  - controllers/ REST handlers (request/response mapping)
  - routers/     Versioned API routing (/api/v1/...)
  - core/        Cross-cutting: resilience, queue, recovery, middleware
"""
__version__ = "1.0.0"