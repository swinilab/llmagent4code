# Architectural Decision Records (ADR)

## ADR-001: Python with FastAPI Framework

### Decision
Use Python with FastAPI as the web framework for the OMS backend.

### Context
- **NFR 1.1 (Response Time)**: Need async support for minimizing latency
- **NFR 1.2 (Concurrency)**: Must efficiently utilize server resources
- **NFR 1.3 (Queue Management)**: Handle traffic spikes gracefully

### Alternatives Considered
1. **Java Spring Boot**: 
   - Rejected due to higher memory footprint and longer startup times
   - More verbose configuration
   - Slower development iteration

2. **Node.js with Express/NestJS**:
   - Rejected due to weaker type safety without TypeScript
   - Less mature async ORM ecosystem
   - Python provides better data validation with Pydantic

3. **Go with Gin/Echo**:
   - Rejected due to less mature ORM ecosystem
   - More boilerplate for validation
   - Python's ecosystem better suited for rapid OMS development

### Consequences
- **Positive**: Fast development, excellent async support, automatic OpenAPI docs
- **Negative**: GIL limits true parallelism (mitigated by async I/O)
- **Trade-off**: Chose development speed and ecosystem over raw performance

---

## ADR-002: Async SQLAlchemy with SQLite/PostgreSQL

### Decision
Use SQLAlchemy 2.0 with async support (aiosqlite for local, asyncpg for production).

### Context
- **NFR 1.1**: Minimize database round-trip latency
- **NFR 1.2**: Efficient connection pooling for high concurrency
- Need ACID compliance for financial transactions

### Alternatives Considered
1. **MongoDB/NoSQL**:
   - Rejected due to lack of ACID transactions for order/payment consistency
   - Complex joins needed for order-line item relationships

2. **Raw SQL with asyncpg**:
   - Rejected due to maintenance burden
   - Loss of ORM benefits for complex domain models

3. **Tortoise ORM**:
   - Rejected due to smaller community and less mature ecosystem
   - SQLAlchemy has better enterprise support

### Consequences
- **Positive**: Type safety, connection pooling, migration support via Alembic
- **Negative**: Slight overhead vs raw SQL
- **Trade-off**: Chose maintainability and safety over micro-optimizations

---

## ADR-003: Layered Architecture (Controller-Service-Repository)

### Decision
Implement clean layered architecture with clear separation of concerns.

### Context
- **NFR 1.2**: Efficient resource utilization through clear boundaries
- Need maintainable codebase for multiple roles (Customer, Staff, Accountant)
- Testability requirements

### Alternatives Considered
1. **Monolithic Service Layer**:
   - Rejected due to tight coupling
   - Difficult to test and maintain

2. **CQRS Pattern**:
   - Rejected as over-engineering for this scale
   - Added complexity not justified by requirements

3. **Hexagonal Architecture**:
   - Considered but rejected for simplicity
   - Layered architecture sufficient for current needs

### Consequences
- **Positive**: Clear separation, easy testing, maintainable
- **Negative**: More files and boilerplate
- **Trade-off**: Chose clarity over minimalism

---

## ADR-004: In-Memory Session State (Stateless API)

### Decision
Implement stateless REST API with no server-side session state.

### Context
- **NFR 1.2**: Scale horizontally in Kubernetes
- **NFR 1.3**: Handle traffic spikes without session affinity

### Alternatives Considered
1. **Server-side Sessions (Redis)**:
   - Rejected as authentication is not required
   - Adds infrastructure complexity

2. **JWT Tokens**:
   - Rejected as per requirements (no authentication)
   - Would add unnecessary complexity

3. **Session Cookies**:
   - Rejected for same reasons as server-side sessions

### Consequences
- **Positive**: Easy horizontal scaling, simple deployment
- **Negative**: No user tracking across requests (not required)
- **Trade-off**: Chose simplicity as auth is out of scope

---

## ADR-005: SQLite for Development, PostgreSQL for Production

### Decision
Use SQLite for local development with easy migration to PostgreSQL.

### Context
- **NFR 1.2**: Local development should be lightweight
- Production needs robust RDBMS for concurrency

### Alternatives Considered
1. **PostgreSQL Everywhere**:
   - Rejected due to setup complexity for developers
   - Overkill for local testing

2. **Docker Compose for Local DB**:
   - Rejected to minimize local dependencies
   - SQLite sufficient for development testing

3. **In-Memory Database**:
   - Rejected due to data persistence needs
   - Testing should be realistic

### Consequences
- **Positive**: Zero setup for developers, production-ready config
- **Negative**: Minor SQL dialect differences
- **Trade-off**: Chose developer experience with production parity

---

## ADR-006: Pydantic v2 for Data Validation

### Decision
Use Pydantic v2 for request/response validation and serialization.

### Context
- **NFR 1.1**: Fast validation for low-latency responses
- Need automatic OpenAPI schema generation
- Type safety for domain models

### Alternatives Considered
1. **Marshmallow**:
   - Rejected due to slower performance
   - Less integrated with FastAPI

2. **attrs + manual validation**:
   - Rejected due to boilerplate
   - No automatic OpenAPI support

3. **dataclasses + validation**:
   - Rejected for same reasons as attrs
   - Pydantic provides better DX

### Consequences
- **Positive**: Fast validation, automatic docs, type safety
- **Negative**: Additional dependency
- **Trade-off**: Chose ecosystem integration over minimalism
