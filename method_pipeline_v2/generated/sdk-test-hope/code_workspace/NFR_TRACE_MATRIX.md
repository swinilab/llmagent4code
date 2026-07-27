| NFR ID | Architectural Mechanism | Module/Component | Verification Method |
|--------|------------------------|------------------|---------------------|
| NFR 1.1 Response Time | Async endpoints + aiocache response caching | app/services.py, app/cache/response_cache.py | Load test with k6 shows p95 latency < 200ms for checkout endpoint |
| NFR 1.2 Concurrency & Resource Utilization | FastAPI running under uvicorn workers, async IO | app/main.py | ab -c 100 shows throughput scales near-linearly up to worker count |
| NFR 1.3 Queue Management | asyncio.Queue with bounded size | app/queue/queue_manager.py | Burst of 1000 requests returns 202 without dropped connections; queue size bounded |
| NFR 2.1 Graceful Degradation | Middleware disables non‑essential routes when DEGRADE env var set | app/degradation/degradation_manager.py | Set DEGRADE=1; non‑essential endpoints return 503 while core remain 2xx |
| NFR 2.2 Fault Detection and Recovery | Tenacity retries on DB connection creation | app/db/connection_pool.py, app/health/liveness.py | Kill DB; /ready recovers after retry attempts |
| NFR 2.3 State Preservation | Write‑ahead log persisted in SQLite | app/persistence/wal.py | Kill process mid‑queue; replay_wal_on_startup restores pending tasks |
