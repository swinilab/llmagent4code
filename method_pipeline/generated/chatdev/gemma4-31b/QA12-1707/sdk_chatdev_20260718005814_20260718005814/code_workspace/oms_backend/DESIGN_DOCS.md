# NFR Traceability Matrix
# | NFR | Architectural Mechanism | Module | Verification Method |
# |---|---|---|---|
# | 1.1 Response Time | AsyncIO + SQLAlchemy Async Session | `database.py`, `controllers` | Measure API response times using `timeit` or Load testing tools. |
# | 1.2 Concurrency | FastAPI (ASGI) + Async Database Drivers | `main.py`, `database.py` | Run concurrent requests using `locust` or `ab` and monitor CPU/RAM. |
# | 1.3 Queue Management | Async Event Loop + Connection Pooling | `database.py` | Simulate spike in requests; verify system doesn't crash via health check. |
# | 2.1 Graceful Degradation | Circuit Breaker/Timeout logic in Services | `services/` | Simulate high latency in a sub-service and verify core checkout still works. |
# | 2.2 Fault Detection | Exception Middleware + Auto-retry logic | `main.py` | Kill a simulated external service; verify system recovers on restart/retry. |
# | 2.3 State Preservation | Persistent SQLite Database (WAL mode) | `database.py` | Crash app during order processing; verify state is restored on reboot. |

# Architectural Decision Records (ADR)
# 
# ADR 1: Database Choice
# Decision: SQLite with SQLAlchemy (Async)
# Context: NFR 2.3 (State Preservation), Local Deployment.
# Alternatives: PostgreSQL (Overkill for local demo), MongoDB (Schema-less, less suited for financial transactions).
# Consequences: Limited to single-instance write, but perfect for local production-grade demonstration.
#
# ADR 2: Framework Choice
# Decision: FastAPI
# Context: NFR 1.1 (Response Time), NFR 1.2 (Concurrency).
# Alternatives: Flask (Synchronous by default), Django (Heavier boilerplate).
# Consequences: Requires async programming throughout the stack.
#
# ADR 3: State Management
# Decision: Status-based State Machine in Order Service
# Context: User Workflow implementation.
# Alternatives: Temporal.io (Too complex), Manual flags (Error prone).
# Consequences: Strict transitions ensure business logic integrity.
