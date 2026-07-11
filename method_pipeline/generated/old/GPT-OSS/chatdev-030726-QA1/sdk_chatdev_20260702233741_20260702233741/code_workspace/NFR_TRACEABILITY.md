# NFR Traceability Matrix

| NFR | Architectural Mechanism | Module / Component | Verification Method |
|-----|------------------------|--------------------|--------------------|
| **1.1 Response Time** | FastAPI async endpoints + Uvicorn ASGI server | `app/main.py`, all routers in `app/controllers.py` | Run load test (e.g., `hey -n 1000 -c 50`) and assert 95th percentile < 200 ms |
| **1.2 Concurrency & Resource Utilization** | PostgreSQL connection pooling + SQLAlchemy sessions; Docker Compose scaling of `api` service; Celery workers for async tasks | `app/dependencies.py` (engine pool), `docker-compose.yml` (scale option) | Observe CPU/RAM via `docker stats` under load; ensure no thread starvation |
| **1.3 Queue Management** | Celery + Redis queue to buffer spikes; tasks are idempotent and retried | `app/queue.py` (Celery app), `app/services.py` (async verification placeholder) | Publish a burst of 10k verification tasks; monitor Redis queue length and ensure no crashes |

*All NFRs are traceable to concrete code artifacts and can be validated with the described methods.*
