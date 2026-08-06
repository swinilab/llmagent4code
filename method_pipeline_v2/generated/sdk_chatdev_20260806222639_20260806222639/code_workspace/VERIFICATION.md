# NFR Verification Steps

This document describes how to verify that each Non-Functional Requirement (NFR) is satisfied by the implementation.

---

## NFR 1.1: Limit Event Response

**Requirement:** Process events only up to a set maximum rate.

**Implementation:** Token bucket rate limiting in `oms_backend/utils/rate_limiter.py`

**Verification Steps:**

1. Start the application:
   ```bash
   docker-compose -f iac/docker-compose.yml up -d
   ```

2. Send rapid requests to any POST endpoint:
   ```bash
   # Install jq for JSON parsing
   # Send 150 requests in quick succession
   for i in {1..150}; do
     curl -s -o /dev/null -w "%{http_code}\n" \
       -X POST http://localhost:8000/api/v1/customers \
       -H "Content-Type: application/json" \
       -d '{"name":"Test User","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}'
   done | sort | uniq -c
   ```

3. **Expected Result:**
   - First ~100 requests return `201`
   - Subsequent requests return `429` (Too Many Requests)

4. **Code Location:**
   - `oms_backend/utils/rate_limiter.py::RateLimiter.is_allowed`
   - Called in each controller's create endpoint

---

## NFR 1.2: Maintain Multiple copies of Data

**Requirement:** Maintain multiple copies of data through caching.

**Implementation:** Redis caching with in-memory fallback in `oms_backend/utils/cache.py`

**Verification Steps:**

1. Start the application with Redis:
   ```bash
   docker-compose -f iac/docker-compose.yml up -d
   ```

2. Create a customer:
   ```bash
   curl -X POST http://localhost:8000/api/v1/customers \
     -H "Content-Type: application/json" \
     -d '{"name":"Test User","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}'
   ```

3. Check Redis for cached data:
   ```bash
   docker exec oms_redis redis-cli KEYS "cache:*"
   ```

4. Get the customer (should hit cache):
   ```bash
   curl http://localhost:8000/api/v1/customers/<customer-id>
   ```

5. **Test Graceful Degradation** - Stop Redis:
   ```bash
   docker stop oms_redis
   ```

6. Make another request - should still work with in-memory cache:
   ```bash
   curl http://localhost:8000/api/v1/customers/<customer-id>
   ```

7. **Expected Result:**
   - Cache keys visible in Redis
   - API continues working when Redis is stopped (graceful degradation)

8. **Code Location:**
   - `oms_backend/utils/cache.py::CacheManager.get/set`
   - `oms_backend/repository/base.py::BaseRepository.get_by_id`

---

## NFR 2.1: Exception Detection

**Requirement:** Detect system conditions that alter normal flow (system exceptions and timeouts).

**Implementation:** Structured exception hierarchy in `oms_backend/utils/exceptions.py`

**Verification Steps:**

1. **Test Validation Exception (System Exception):**
   ```bash
   # Send invalid data (name too short)
   curl -X POST http://localhost:8000/api/v1/customers \
     -H "Content-Type: application/json" \
     -d '{"name":"A","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}'
   ```
   **Expected:** `400 Bad Request` with validation error message

2. **Test Not Found Exception:**
   ```bash
   curl http://localhost:8000/api/v1/customers/00000000-0000-0000-0000-000000000000
   ```
   **Expected:** `404 Not Found`

3. **Test Invalid UUID Format:**
   ```bash
   curl http://localhost:8000/api/v1/customers/invalid-uuid
   ```
   **Expected:** `400 Bad Request` with "Invalid UUID format"

4. **Code Location:**
   - `oms_backend/utils/exceptions.py::OMSException` and subclasses
   - `oms_backend/utils/retry.py::execute_with_retry`

---

## NFR 2.2: Graceful Degradation

**Requirement:** Maintain critical system functions in presence of component failures.

**Implementation:** Fallback mechanisms in cache and rate limiter

**Verification Steps:**

1. Start the application:
   ```bash
   docker-compose -f iac/docker-compose.yml up -d
   ```

2. Stop Redis:
   ```bash
   docker stop oms_redis
   ```

3. Make API requests - should continue working:
   ```bash
   curl http://localhost:8000/health
   curl -X POST http://localhost:8000/api/v1/customers \
     -H "Content-Type: application/json" \
     -d '{"name":"Test User","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}'
   ```

4. **Expected Result:**
   - API continues to function
   - Uses in-memory fallback for caching
   - Rate limiting allows requests (fails open)

5. **Code Location:**
   - `oms_backend/utils/cache.py::CacheManager.get` (try/except RedisError)
   - `oms_backend/utils/rate_limiter.py::RateLimiter.is_allowed` (try/except RedisError)

---

## NFR 2.3: State Resynchronization

**Requirement:** States of active and standby components are periodically compared to ensure synchronization.

**Implementation:** State synchronization in `oms_backend/utils/retry.py::synchronize_state`

**Verification Steps:**

1. Create a customer:
   ```bash
   RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/customers \
     -H "Content-Type: application/json" \
     -d '{"name":"Test User","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}')
   CUSTOMER_ID=$(echo $RESPONSE | jq -r '.id')
   ```

2. Get customer (populates cache):
   ```bash
   curl http://localhost:8000/api/v1/customers/$CUSTOMER_ID
   ```

3. Check cache exists:
   ```bash
   docker exec oms_redis redis-cli GET "cache:customer:$CUSTOMER_ID"
   ```

4. The `resynchronize` method is called on updates to ensure cache matches database.

5. **Code Location:**
   - `oms_backend/utils/retry.py::synchronize_state`
   - `oms_backend/repository/base.py::BaseRepository.resynchronize`

---

## NFR 2.4: Transactions

**Requirement:** Ensure ACID properties for asynchronous messages between distributed components.

**Implementation:** SQLAlchemy transaction management in `oms_backend/infrastructure/database.py`

**Verification Steps:**

1. **Test Atomic Order Creation:**
   ```bash
   # First create a customer
   CUSTOMER=$(curl -s -X POST http://localhost:8000/api/v1/customers \
     -H "Content-Type: application/json" \
     -d '{"name":"Test User","address":"123 Test St","phone":"+1234567890","bankingDetails":{"accountNumber":"123456789","bankName":"Test Bank"},"role":"CUSTOMER"}')
   CUSTOMER_ID=$(echo $CUSTOMER | jq -r '.id')
   
   # Create a product
   PRODUCT=$(curl -s -X POST http://localhost:8000/api/v1/products \
     -H "Content-Type: application/json" \
     -d '{"description":"Test Product","price":{"amount":"99.99","currency":"USD"}}')
   PRODUCT_ID=$(echo $PRODUCT | jq -r '.id')
   ```

2. **Test with Invalid Product (should rollback):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/orders \
     -H "Content-Type: application/json" \
     -d "{\"customerRef\":\"$CUSTOMER_ID\",\"lineItems\":[{\"productRef\":\"00000000-0000-0000-0000-000000000000\",\"quantity\":1}]}"
   ```
   **Expected:** `404 Not Found` - order not created (transaction rolled back)

3. **Test with Valid Data (should succeed atomically):**
   ```bash
   curl -X POST http://localhost:8000/api/v1/orders \
     -H "Content-Type: application/json" \
     -d "{\"customerRef\":\"$CUSTOMER_ID\",\"lineItems\":[{\"productRef\":\"$PRODUCT_ID\",\"quantity\":2}]}"
   ```
   **Expected:** `201 Created` with order including computed totalAmount

4. **Verify Order Status State Machine:**
   ```bash
   ORDER_ID=<order-id-from-response>
   
   # Try invalid transition (PLACED -> PAID should fail)
   curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/verify
   # Expected: 409 Conflict
   
   # Valid transition (PLACED -> ACCEPTED)
   curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/accept
   # Expected: 200 OK with status "ACCEPTED"
   ```

5. **Code Location:**
   - `oms_backend/infrastructure/database.py::TransactionManager`
   - `oms_backend/service/order_service.py::OrderService.create_order`

---

## Complete Workflow Verification

Test the complete order workflow:

```bash
# 1. Customer places order
ORDER=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customerRef\":\"$CUSTOMER_ID\",\"lineItems\":[{\"productRef\":\"$PRODUCT_ID\",\"quantity\":1}]}")
ORDER_ID=$(echo $ORDER | jq -r '.id')

# 2. Order Staff accepts order
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/accept

# 3. Accountant creates invoice
INVOICE=$(curl -s -X POST http://localhost:8000/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"orderRef\":\"$ORDER_ID\",\"billingInfo\":{\"name\":\"Test User\",\"address\":\"123 Test St\"},\"totalAmount\":\"99.99\"}")

# 4. Customer pays invoice
PAYMENT=$(curl -s -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"orderRef\":\"$ORDER_ID\",\"amount\":\"99.99\",\"method\":\"CREDIT_CARD\"}")
PAYMENT_ID=$(echo $PAYMENT | jq -r '.id')

# 5. Accountant verifies payment
curl -X POST http://localhost:8000/api/v1/payments/$PAYMENT_ID/verify

# 6. Order Staff ships order
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/ship

# 7. Order Staff closes order
curl -X POST http://localhost:8000/api/v1/orders/$ORDER_ID/close

# Verify final status
curl http://localhost:8000/api/v1/orders/$ORDER_ID | jq '.status'
# Expected: "CLOSED"
```
