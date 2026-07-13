# ADR 0002: Architectural Style

## Status
Accepted

## Context
We need to decide on the architectural style for the OMS. Options include microservices, modular monolith, or layered architecture. The system must handle non-trivial traffic but does not require extreme scale that necessitates microservices. We also want to maintain simplicity in development, testing, and deployment.

## Decision
We adopt a **modular monolith** architecture. The application is a single deployable unit but is internally divided into clearly defined modules (domains) such as customer, order, product, payment, invoice. Each module encapsulates its own models, services, schemas, and API endpoints. Communication between modules is through well-defined interfaces (service calls) rather than direct database access.

## Consequences
### Pros
- Simpler deployment and operational overhead compared to distributed microservices.
- Easier testing and debugging due to in-process calls.
- Ability to evolve towards microservices later if needed by extracting modules into separate services.
- Consistent transaction boundaries (single database) simplifying data consistency.
- Shared libraries and reduced network latency.

### Cons
- Potential for tighter coupling if modules are not properly isolated.
- Scaling requires scaling the entire application rather than independent components.
- Risk of monolith growing too large over time.

### Mitigation
- Enforce module boundaries via code reviews and linting.
- Keep each module focused on a single responsibility.
- Use dependency injection to facilitate loose coupling.
- Monitor code modularity and refactor as needed.
