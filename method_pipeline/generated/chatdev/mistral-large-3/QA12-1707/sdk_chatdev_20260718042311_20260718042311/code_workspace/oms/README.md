# Order Management System (OMS)

A production-grade, backend-only e-commerce Order Management System (OMS) with support for:
- Customer ordering
- Payment processing
- Invoicing
- Shipping
- Closure

## Features
- **State Preservation (NFR 2.3):** Persists pending orders and outbox events to ensure recovery after crashes.
- **Fault Detection and Recovery (NFR 2.2):** Automatically recovers failed tasks and pending operations on startup.
- **Concurrency & Queue Management (NFR 1.2, NFR 1.3):** Uses Celery with Redis for task queueing and persistence.
- **Graceful Degradation (NFR 2.1):** Middleware ensures core functionality remains available under load.

## Setup
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd oms
   ```

2. **Start the services:**
   ```bash
   docker-compose up --build
   ```

3. **Access the API:**
   - FastAPI: `http://localhost:8000`
   - Flower (Celery Dashboard): `http://localhost:5555`

## Verification of State Preservation (NFR 2.3)
1. Start the application and place an order.
2. Simulate a crash by killing the Celery worker:
   ```bash
   docker-compose restart celery
   ```
3. Restart the application and verify that pending orders and outbox events are recovered and processed.

## Verification of Fault Detection and Recovery (NFR 2.2)
1. Trigger a task failure (e.g., by stopping Redis during task execution).
2. Restart the application and verify that failed tasks are requeued and processed.

## Verification of Concurrency & Queue Management (NFR 1.2, NFR 1.3)
1. Simulate a traffic spike by sending multiple concurrent requests.
2. Verify that Celery tasks are processed without loss or duplication.

## Verification of Graceful Degradation (NFR 2.1)
1. Simulate high load (e.g., using `locust`).
2. Verify that non-essential features degrade while core checkout functionality remains available.