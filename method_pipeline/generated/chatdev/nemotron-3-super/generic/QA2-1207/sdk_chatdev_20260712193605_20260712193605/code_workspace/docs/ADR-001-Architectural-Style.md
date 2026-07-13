# ADR 001: Architectural Style

## Status
Accepted

## Context
We need to decide on the architectural style for the OMS backend. The system must handle non-trivial traffic and serve three roles (Customer, Order Staff, Accountant). We are building a backend-only system that will be deployed as a single unit (though it can be scaled horizontally).

## Decision
We chose a monolithic architecture with a clear separation of layers (controllers, services, repositories, models). This monolith will be deployed as a single service but designed to be modular enough to eventually split into microservices if needed.

## Consequences
### Pros
- Simpler development, testing, and deployment.
- No network latency between components.
- Easier to maintain ACID transactions across modules.
- Simpler to reason about data consistency.

### Cons
- Scaling requires scaling the entire application (though we can scale horizontally by running multiple instances).
- Potential for the monolith to grow complex over time.
- Technological lock-in (though we can mitigate by using well-defined interfaces).

## Alternatives Considered
1. **Microservices**: We considered breaking the system into services (e.g., Order Service, Payment Service, Inventory Service). However, this adds complexity in terms of inter-service communication, distributed transactions, and operational overhead. Given the scope and the requirement for a production-grade but not necessarily web-scale system, a monolith is more appropriate.

2. **Serverless**: We considered using serverless functions (e.g., AWS Lambda) for each endpoint. However, this would complicate state management and increase cold start latency, which is not ideal for a system requiring low-latency order processing.

## Implications
This decision affects the deployment, scaling, and team structure. We will organize the codebase in a modular way to facilitate future migration to microservices if the need arises.