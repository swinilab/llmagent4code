# ADR 0004: Caching Strategy

## Status
Accepted

## Context
The product catalog is read-heavy and relatively static compared to transactional data. Frequent database reads for product listings can increase latency and database load, especially under high traffic. To improve response times and reduce database pressure, we introduce caching.

## Decision
We will use Redis as a read-through cache for product data. On product read requests (GET /products, GET /products/{id}), the service will first attempt to fetch from Redis cache. On cache miss, it will query the database, store the result in Redis with a TTL (e.g., 5 minutes), and return the data. Product updates (create, update, delete) will invalidate the relevant cache entries.

## Consequences
### Pros
- Reduced latency for product catalog requests.
- Decreased database load, freeing resources for write-heavy operations.
- Improved scalability for read-heavy workloads.

### Cons
- Cache invalidation complexity: ensuring consistency between cache and database.
- Stale data risk if TTL is too long or invalidation fails.
- Additional operational overhead (Redis cluster management).

### Mitigation
- Use cache-aside pattern with explicit invalidation on updates.
- Set reasonable TTL based on data volatility.
- Monitor cache hit/miss ratios and adjust TTL as needed.
- Consider using Redis pub/sub to invalidate caches across instances.
