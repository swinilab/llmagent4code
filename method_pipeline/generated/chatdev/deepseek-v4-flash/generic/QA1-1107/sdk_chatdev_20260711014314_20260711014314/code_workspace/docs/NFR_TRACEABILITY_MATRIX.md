# NFR Traceability Matrix

| NFR | Architectural Mechanism | Module/Component | Verification Method |
|-----|------------------------|-------------------|---------------------|
| **NFR 1.1 — Response Time** | FastAPI async handlers; eager-loaded relationships (selectinload); pagination on all list endpoints; database indexing on foreign keys; rate limiter prevents abuse | `app/main.py` (FastAPI app), `app/services/order_service.py` (selectinload), `app/controllers/*` (pagination), `app/middleware/rate_limiter.py` | Run `httpx` load test with 100 concurrent requests against `/api/v1/products?search=test`; verify p95 response time < 200ms |
| **NFR 1.2 — Concurrency & Resource Utilization** | Async SQLAlchemy engine with connection pooling (pool_size=20, max_overflow=10); uvicorn with 4 workers; asyncio event loop for non-blocking I/O; background task processor with configurable worker count | `app/database.py` (engine config), `app/config.py` (pool settings), `app/tasks/background.py` (worker pool) | Run `uvicorn` with 4 workers; monitor CPU utilization with `htop`; verify CPU stays below 70% under 500 concurrent requests |
| **NFR 1.3 — Queue Management** | Bounded asyncio.Queue (maxsize=1000) with backpressure; configurable worker pool (4 workers); timeout-based enqueue (5s); graceful rejection with logging; Celery with `task_acks_late` and `worker_prefetch_multiplier=1` for production | `app/tasks/background.py` (queue config), `app/celery_app.py` (Celery config), `app/middleware/rate_limiter.py` (load shedding) | Flood background queue with 2000+ tasks via `enqueue()`; verify queue rejects at capacity (maxsize=1000) with "Background queue full" log message instead of crashing |

## Detailed Verification Steps

### NFR 1.1 — Response Time Verification

```bash
# Start the server
uv run uvicorn app.main:app --port 8000 &

# Run a simple load test
uv run python -c "
import asyncio, httpx, time

async def load_test():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # Create a product first
        resp = await client.post('/api/v1/products/', json={
            'description': 'Test Product',
            'pricing': {'base_price': 10.0, 'currency': 'USD'}
        })
        product = resp.json()

        # Measure search response time
        times = []
        for _ in range(50):
            start = time.perf_counter()
            resp = await client.get(f'/api/v1/products/?search=Test')
            times.append((time.perf_counter() - start) * 1000)

        times.sort()
        print(f'Min: {times[0]:.2f}ms')
        print(f'p50: {times[25]:.2f}ms')
        print(f'p95: {times[47]:.2f}ms')
        print(f'p99: {times[49]:.2f}ms')
        print(f'Max: {times[-1]:.2f}ms')

asyncio.run(load_test())
"
```

### NFR 1.2 — Concurrency & Resource Utilization Verification

```bash
# Start with 4 workers
uv run uvicorn app.main:app --port 8000 --workers 4 &

# Monitor in another terminal
htop

# Run concurrent requests
uv run python -c "
import asyncio, httpx

async def concurrent_test():
    async def make_request(client):
        resp = await client.get('/api/v1/products/')
        return resp.status_code

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        tasks = [make_request(client) for _ in range(500)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if r == 200)
        print(f'Successful: {success}/{len(results)}')

asyncio.run(concurrent_test())
"
```

### NFR 1.3 — Queue Management Verification

```bash
# Start the server
uv run uvicorn app.main:app --port 8000 &

# Flood the background queue
uv run python -c "
import asyncio
from app.tasks.background import get_task_processor

async def flood_queue():
    processor = get_task_processor()
    await processor.start()

    async def dummy_task(msg):
        await asyncio.sleep(0.1)
        return msg

    count = 0
    for i in range(2000):
        try:
            await processor.enqueue(dummy_task, f'task-{i}')
            count += 1
        except asyncio.QueueFull:
            print(f'Queue full after {count} tasks (expected ~1000)')
            break
        except Exception as e:
            print(f'Error at task {i}: {e}')
            break

    await processor.stop()

asyncio.run(flood_queue())
"
```
