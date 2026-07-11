# NFR Traceability Matrix

| NFR ID | Requirement | Architectural Mechanism | Module/Component | Verification Method |
|--------|-------------|------------------------|------------------|---------------------|
| **NFR 1.1** | Response Time: Core journeys must minimize round-trip latency under load | Async I/O with connection pooling, eager loading for related entities | `oms/config/database.py` (engine config), `oms/repositories/*.py` (selectinload) | Load test with `wrk` - measure p95 latency < 200ms for GET endpoints |
| **NFR 1.1** | Response Time: Fast validation | Pydantic v2 with compiled validators | `oms/models/schemas.py` | Benchmark validation time < 1ms per request |
| **NFR 1.1** | Response Time: Efficient serialization | Pydantic `model_validate()` with `from_attributes=True` | All `*Response` schemas | Profile serialization time in load tests |
| **NFR 1.2** | Concurrency: Async request handling | FastAPI with uvicorn workers, async/await throughout | `oms/app.py`, all services | Deploy with 4 workers, verify 1000+ concurrent connections |
| **NFR 1.2** | Concurrency: Connection pooling | SQLAlchemy async engine with pool_size=20, max_overflow=40 | `oms/config/database.py` | Monitor pool stats under load, verify no connection exhaustion |
| **NFR 1.2** | Concurrency: Database indexes | Composite indexes on frequently queried columns | `oms/models/entities.py` (`__table_args__`) | EXPLAIN QUERY PLAN shows index usage |
| **NFR 1.2** | Resource Utilization: Memory efficiency | Generator-based session management, no global state | `oms/config/database.py` (`get_db_session`) | Monitor memory under load, verify stable RSS |
| **NFR 1.3** | Queue Management: Request timeout handling | Uvicorn timeout configuration, async cancellation | `server.py` (uvicorn.run config) | Send slow requests, verify timeout after configured duration |
| **NFR 1.3** | Queue Management: Error handling | Global exception handler, transaction rollback | `oms/app.py` (`global_exception_handler`), `database.py` | Trigger errors, verify proper 500 responses and rollback |
| **NFR 1.3** | Queue Management: Graceful degradation | HTTP 429/503 responses, circuit breaker pattern ready | Controller error handling | Simulate overload, verify appropriate status codes |
| **NFR 2.1** | API Versioning | URL path versioning (`/api/v1/`) | All controllers (`prefix="/api/v1/..."`) | Verify all endpoints have version prefix |
| **NFR 2.2** | OpenAPI Documentation | Automatic OpenAPI 3.0 generation | `oms/app.py` (FastAPI config) | Access `/docs` and `/openapi.json`, verify completeness |
| **NFR 2.3** | Health Checks | Dedicated health endpoints | `oms/app.py` (`/health`, `/ready`) | Kubernetes probes can query endpoints |
| **NFR 3.1** | Data Integrity: ACID transactions | SQLAlchemy async sessions with commit/rollback | `oms/config/database.py` | Verify atomic operations in service methods |
| **NFR 3.2** | Data Integrity: Foreign key constraints | SQLAlchemy relationships with cascade | `oms/models/entities.py` | Attempt invalid FK insert, verify constraint error |
| **NFR 3.3** | Data Integrity: Enum validation | Python enums + SQL Enum types | `oms/models/entities.py`, `oms/models/schemas.py` | Attempt invalid status, verify validation error |

---

## Verification Commands

### NFR 1.1 - Response Time
```bash
# Install wrk for load testing
# Run load test on product search endpoint
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/products/available

# Expected: p95 latency < 200ms
```

### NFR 1.2 - Concurrency
```bash
# Check connection pool stats (add debug endpoint)
curl http://localhost:8000/debug/pool-stats

# Run concurrent order creation
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/orders &
done
wait

# Expected: All requests complete without connection errors
```

### NFR 1.3 - Queue Management
```bash
# Test error handling
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'

# Expected: 422 Validation Error with details

# Test transaction rollback (create order with insufficient stock)
# Expected: 400 error, stock unchanged
```

### NFR 2.2 - OpenAPI
```bash
# Verify OpenAPI spec
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# Expected: All endpoints listed with proper versioning
```

### NFR 2.3 - Health Checks
```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status": "healthy", "version": "1.0.0", "timestamp": "..."}

# Readiness check
curl http://localhost:8000/ready

# Expected: {"ready": true}
```
