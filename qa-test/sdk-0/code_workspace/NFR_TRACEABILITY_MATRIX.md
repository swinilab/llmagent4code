# NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-------------------|---------------------|
| **NFR 1.1 Response Time** | Caching of product list + FastAPI timing middleware | `app/cache/response_cache.py`, `app/main.py` | Load test (k6) shows p95 latency < 200 ms for checkout endpoint |
| **NFR 1.2 Concurrency & Resource Utilization** | Uvicorn workers (multiple processes) + asyncio concurrency in services | `app/main.py`, `app/services/order_service.py`, `app/services/payment_service.py`, `app/services/invoice_service.py` | `ab -c 100` shows throughput scales near‑linearly with worker count |
| **NFR 1.3 Queue Management** | Bounded ``asyncio.Queue`` with back‑pressure | `app/queue/queue_manager.py` | Burst of 1000 requests returns 202 Accepted; queue size never exceeds 5000 |
| **NFR 2.1 Graceful Degradation** | Feature‑toggle flag that pauses queue workers and disables non‑essential endpoints | `app/degradation/degradation_manager.py` | Kill background worker under load; checkout still works while `/products/search` returns 503 |
| **NFR 2.2 Fault Detection and Recovery** | Tenacity retry on DB connections and external gateway calls | `app/health/liveness.py`, `app/db/connection_pool.py`, `app/services/payment_service.py` | Simulate DB outage; system automatically reconnects and health endpoint recovers |
| **NFR 2.3 State Preservation** | SQLite WAL + custom write‑ahead log for pending tasks | `app/db/migrations.py`, `app/persistence/wal.py` | Crash process mid‑queue; after restart pending orders resume from WAL with no loss |
