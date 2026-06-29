# Bug Fixes Summary

## All bugs identified in the review have been fixed.

### Critical/High Severity

1. **RateLimitFilter - Counter Never Resets & Thread Safety**
   - Implemented sliding window rate limiting with automatic reset
   - Used `LongAdder` for thread-safe high-concurrency counting
   - Added `AtomicLong` for window management with CAS operations
   - Made rate limit configurable via `AppProperties`

2. **InvoiceService - Subtotal Calculation**
   - Changed to calculate subtotal directly from order items
   - Removed circular dependency on order totals

### Medium Severity

3. **Test Class Visibility**
   - Changed test class to `public` for proper JUnit discovery

4. **Maven Wrapper**
   - Replaced with complete Apache Maven Wrapper script v3.2.0
   - Added `.mvn/wrapper/maven-wrapper.properties`

5. **Order Status Workflow**
   - Added `REVIEWING` state transition in `OrderService.reviewOrder()`

6. **Payment Status Workflow**
   - Added `PAYMENT_PENDING` state in `PaymentService.createPayment()`
   - Added order status reversion on payment failure

### Low Severity

7. **Redundant Resilience4j Config**
   - Deleted `ResilienceConfig.java` (config exists in `application.yml`)

### Already Correct (Verified)

8. **DegradationFilter** - Both recommendations and analytics endpoints protected
9. **docker-compose.yml** - pgAdmin service already defined
