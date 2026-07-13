# ADR 0003: Asynchronous Payment Processing

## Status
Accepted

## Context
Payment processing often involves external gateways and can be slow or unreliable. Performing payment processing synchronously in the API request thread can lead to poor response times, thread exhaustion under load, and poor user experience. We need to ensure the system remains responsive during traffic spikes and gracefully handles external service delays.

## Decision
We will process payments asynchronously using Celery workers. When a customer submits a payment, the API will create a Payment record with status `PENDING` and enqueue a Celery task to process the payment (simulate gateway interaction). The task will update the payment status to `COMPLETED` or `FAILED` and update the associated order and invoice statuses accordingly. This decouples the API response time from the payment processing latency.

## Consequences
### Pros
- API endpoints remain responsive; users receive immediate acknowledgment.
- System can handle higher concurrency as worker processes can be scaled independently.
- Failure isolation: payment processing issues do not block other requests.
- Retry mechanisms can be built into Celery tasks for transient failures.

### Cons
- Increased complexity: need to manage Celery workers, broker, and result backend.
- Eventual consistency: there may be a delay between payment submission and status update.
- Requires careful handling of idempotency to avoid duplicate processing.

### Mitigation
- Provide clear API responses indicating payment is being processed.
- Use idempotency keys in payment requests to prevent duplicate charges.
- Monitor Celery queues and worker health.
- Implement retry policies with exponential backoff for external gateway calls.
