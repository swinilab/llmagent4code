# Verification of Non-Functional Requirements

This document outlines how to verify that the system meets the specified non-functional requirements.

## NFR 1.1: Response Time
**Requirement:** Core journeys (product search, cart, checkout) must minimize round-trip latency under load.

**Verification:**
1. Use a load testing tool (e.g., Locust, k6) to simulate concurrent users performing:
   - Product listing (GET /products)
   - Product retrieval (GET /products/{id})
   - Order creation (POST /orders with items)
2. Measure 95th percentile response times under increasing load (e.g., 10, 50, 100 concurrent users).
3. Acceptance criteria: 95th percentile < 500ms for individual API calls under expected load.

**Steps:**
```bash
# Install locust
pip install locust

# Create a locustfile.py (see examples online)
# Run locust
locust -f locustfile.py --host=http://localhost:8000
```

## NFR 1.2: Concurrency & Resource Utilization
**Requirement:** System must exploit available server resources with minimal queuing.

**Verification:**
1. During load testing (as above), monitor system resources:
   - CPU usage (should increase with load but not saturate prematurely)
   - Memory usage (should remain stable)
   - Number of active database connections (should be pooled and reused)
2. Verify that throughput (requests/second) increases linearly with concurrency up to the system's limit.
3. Check that average response time does not spike dramatically with moderate load increases.

**Tools:** Use `top`, `htop`, `docker stats`, or cloud monitoring equivalents.

## NFR 1.3: Queue Management
**Requirement:** Sudden traffic spikes must not crash the system.

**Verification:**
1. Use a load testing tool to generate a sudden spike (e.g., jump from 10 to 200 users in 1 second).
2. Monitor for:
   - HTTP 5xx errors (should be minimal)
   - System crashes or unresponsiveness
   - Recovery time after the spike subsides
3. The system should handle the spike gracefully (may queue requests internally) but not fail completely.

**Note:** In the current MVP, we rely on async handling and connection pooling. For production, consider adding a message queue (e.g., Redis/RabbitMQ) for non-critical background tasks.

## NFR 2.1: Graceful Degradation
**Requirement:** Under extreme resource contention, degrade non-essential features to keep core checkout available.

**Verification:**
1. Simulate high CPU/memory load (e.g., using `stress-ng` on the host).
2. While under load:
   - Test core checkout flow: create product, create order, process payment (mocked)
   - Test non-essential features: e.g., bulk product imports, reporting endpoints (if implemented)
3. Core checkout should remain functional (maybe slower) while non-essential features may return errors or be disabled.

**Implementation Note:** This would require feature flags and circuit breakers, which are planned for future enhancements.

## NFR 2.2: Fault Detection & Recovery
**Requirement:** Detect internal component failures and automatically attempt recovery.

**Verification:**
1. **Database Failure:**
   - Stop the database container: `docker stop oms-db`
   - Attempt API calls (should return 503 or similar after retries)
   - Start the database container: `docker start oms-db`
   - Verify that subsequent requests succeed after a brief recovery period
2. **Network Partition:**
   - Simulate network issues (e.g., using `tc` to add latency/packet loss)
   - Verify that the application handles timeouts gracefully and retries where appropriate
3. **Check logs** for error messages and retry attempts.

## NFR 2.3: State Preservation
**Requirement:** After an unexpected crash, restore operational state and resume processing pending orders with minimal data loss.

**Verification:**
1. **Simulate a crash:**
   - Send SIGKILL to the application container: `docker kill -s SIGKILL oms-app`
   - Ensure there are pending orders in the database (status: accepted or invoiced but not paid/shipped)
2. **Restart the application:**
   - Start the container: `docker start oms-app`
3. **Verify:**
   - The application starts without errors
   - Pending orders are still present in the database with correct status
   - No data loss committed transactions (verify via database constraints)
   - New operations can be performed normally

**Note:** Since we use ACID transactions and persistent storage, committed data is safe. The biggest risk is in-flight transactions, which are minimized by keeping transactions short.

## Additional Verification

### Security
- Although authentication is not required per spec, verify that sensitive data (like banking details) is not logged or exposed in error messages.
- Check that HTTPS is used in production (via reverse proxy).

### Scalability
- Verify that the application can run multiple instances behind a load balancer (test with docker-compose scale).

### Observability
- Check that logs are structured and include request IDs for tracing.
- Verify that health endpoints are present and functional.

## Tools Used

- **Locust:** For load testing
- **Docker Stats:** For container resource monitoring
- **SQLAlchemy Echo:** For debugging SQL (set DB_ECHO=true)
- **Uvicorn Access Logs:** For request logging

## Conclusion

By following the verification steps above, one can confirm that the OMS meets the specified non-functional requirements. Any gaps identified during verification should be addressed in subsequent iterations.