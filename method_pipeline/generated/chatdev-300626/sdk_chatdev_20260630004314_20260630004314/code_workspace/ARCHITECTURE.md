# Order Management System - Architecture Documentation

## NFR Traceability Matrix

| NFR | Requirement | Architectural Mechanism | Module/Component | Verification Method |
|-----|-------------|------------------------|------------------|---------------------|
| **NFR 1.1** | Response Time | Spring Cache with @Cacheable, connection pooling (HikariCP), async endpoints | `CacheConfig.java`, `application.yml`, all Service classes | Measure response times under load with `ab` or `wrk`; verify <100ms for cached endpoints |
| **NFR 1.2** | Concurrency & Resource Utilization | HPA autoscaling, JVM tuning (G1GC), Tomcat thread pool, resource limits/requests | `kubernetes/deployment.yaml`, `kubernetes/hpa.yaml`, `Dockerfile` | Monitor `kubectl top pods`; verify HPA scales based on CPU/memory; check JVM metrics via /actuator/metrics |
| **NFR 1.3** | Queue Management | Rate limiting filter (RateLimitFilter), request throttling, Tomcat accept-count | `RateLimitFilter.java`, `application.yml` (tomcat config) | Send 110+ rapid requests per second; verify 429 responses after limit; check X-RateLimit headers |
| **NFR 2.1** | Localization of Changes | Business rules isolated in Service classes, externalized via AppProperties | `OrderService.java`, `InvoiceService.java`, `AppProperties.java` | Update `app.business-rules.*` in ConfigMap; verify changes apply without code change |
| **NFR 2.2** | Interface Stability | Versioned API paths (`/api/v1/`), OpenAPI spec, backward-compatible DTOs | All Controllers in `controller/` directory, `OpenApiConfig.java` | Check OpenAPI spec at `/swagger-ui.html`; verify v1 paths remain stable across releases |
| **NFR 2.3** | Deferred Binding | Spring @ConfigurationProperties, ConfigMap-based config, environment variables | `AppProperties.java`, `kubernetes/configmap.yaml` | Update ConfigMap values; verify changes apply on next request (for dynamic properties) |
| **NFR 3.1** | Graceful Degradation | DegradationFilter, feature flags in AppProperties, selective feature disabling | `DegradationFilter.java`, `AppProperties.java` | Set `app.features.recommendations-enabled=false`; verify /recommendations returns 503 while checkout works |
| **NFR 3.2** | Fault Detection & Recovery | Resilience4j circuit breaker, liveness/readiness probes, actuator health endpoints | `ResilienceConfig.java`, `kubernetes/deployment.yaml`, `application.yml` | Delete pod; verify automatic restart; simulate DB failure; verify circuit breaker opens |
| **NFR 3.3** | State Preservation | PostgreSQL persistent storage, JPA transactions (@Transactional), PVC for database | `kubernetes/pvc.yaml`, all Service classes with @Transactional, `postgres-deployment.yaml` | Create order, restart pod; verify order persists in database via API |

---

## Architectural Decision Records (ADRs)

### ADR 001: Spring Boot 3.x with Java 17

**Decision:** Use Spring Boot 3.x with Java 17 as the backend framework.

**Context:** 
- User explicitly specified Spring Boot 3.x (Java 17+) as fixed tech stack
- Need to satisfy all NFRs including response time, concurrency, and fault tolerance
- Enterprise-grade framework with mature ecosystem for production deployments

**Alternatives Considered:**
1. **Python FastAPI**: Async support, rapid development. Rejected because user explicitly required Spring Boot.
2. **Quarkus**: Native compilation, fast startup. Rejected due to smaller ecosystem and steeper learning curve.
3. **Micronaut**: Compile-time dependency injection. Rejected due to less mature ecosystem compared to Spring.

**Consequences:**
- ✅ Mature ecosystem with extensive documentation and community support
- ✅ Built-in support for caching, resilience, actuator endpoints
- ✅ Strong typing and compile-time safety with Java
- ⚠️ Longer startup time compared to some alternatives
- ⚠️ Higher memory footprint (mitigated via JVM tuning)

---

### ADR 002: PostgreSQL for Production, H2 for Development

**Decision:** Use H2 in-memory database for development and PostgreSQL for production deployments.

**Context:**
- Need to support local development with minimal setup (docker-compose)
- Must satisfy NFR 3.3 (State Preservation)
- Production deployment requires robust, scalable database

**Alternatives Considered:**
1. **PostgreSQL only**: Production-grade, robust. Rejected for development due to added complexity.
2. **MySQL**: Similar to PostgreSQL. Rejected due to PostgreSQL's superior JSON support and features.
3. **In-memory only**: Fastest option. Rejected because it violates NFR 3.3 (State Preservation).

**Consequences:**
- ✅ Zero-config local development with H2
- ✅ Production-grade PostgreSQL with proper persistence
- ✅ Easy migration path via Spring profiles
- ⚠️ Requires DATABASE_URL change between environments
- ⚠️ H2 may not catch all PostgreSQL-specific issues

---

### ADR 003: Raw Kubernetes Manifests over Helm

**Decision:** Use raw Kubernetes YAML manifests instead of Helm charts.

**Context:**
- Need to provide complete, runnable Kubernetes deployment
- Must satisfy NFR 1.2 (Resource Utilization) with HPA
- Team may have varying Helm expertise

**Alternatives Considered:**
1. **Helm Charts**: Industry standard, templating, versioning. Rejected because it adds complexity for simple deployments.
2. **Kustomize**: Kubernetes-native configuration management. Rejected because raw YAML is simpler for this use case.
3. **Docker Compose for K8s (Kompose)**: Auto-conversion. Rejected because it doesn't produce production-grade manifests.

**Consequences:**
- ✅ No additional tooling required (just kubectl)
- ✅ Full visibility into what's deployed
- ✅ Easier to understand and modify
- ⚠️ No built-in versioning or rollback (must use Git)
- ⚠️ More verbose for multiple environments

---

### ADR 004: Resilience4j for Circuit Breaker

**Decision:** Use Resilience4j for circuit breaker and time limiter patterns.

**Context:**
- Must satisfy NFR 3.2 (Fault Detection & Recovery)
- Need to handle transient failures (DB drops, downstream hiccups)
- Spring Cloud CircuitBreaker provides abstraction

**Alternatives Considered:**
1. **Hystrix**: Mature, widely used. Rejected because it's in maintenance mode.
2. **Spring Retry**: Simple retry mechanism. Rejected because it lacks circuit breaker pattern.
3. **Custom implementation**: Full control. Rejected due to maintenance burden and reinventing the wheel.

**Consequences:**
- ✅ Actively maintained with good Spring Boot integration
- ✅ Functional programming style, lightweight
- ✅ Built-in metrics and actuator integration
- ⚠️ Additional dependency to manage
- ⚠️ Learning curve for team unfamiliar with functional patterns

---

### ADR 005: Multi-Stage Docker Build

**Decision:** Use multi-stage Docker build to minimize final image size.

**Context:**
- Need to produce minimal, secure container images
- Must support both docker-compose and Kubernetes deployments
- Security best practices (non-root user, minimal attack surface)

**Alternatives Considered:**
1. **Single-stage build**: Simpler Dockerfile. Rejected because it produces larger images.
2. **Distroless base**: Minimal runtime. Rejected due to debugging difficulty.
3. **Full JDK image**: Easier debugging. Rejected due to security and size concerns.

**Consequences:**
- ✅ Small final image (~200MB vs ~800MB)
- ✅ Non-root user for security
- ✅ Health check built into image
- ⚠️ Slightly more complex build process
- ⚠️ Debugging requires additional tooling

---

### ADR 006: In-Memory Caching with Spring Cache

**Decision:** Use Spring's ConcurrentMapCacheManager for in-memory caching.

**Context:**
- Must satisfy NFR 1.1 (Response Time)
- Need to minimize round-trip latency for core journeys
- Local development simplicity

**Alternatives Considered:**
1. **Redis**: Distributed, survives restarts. Rejected because it adds infrastructure dependency.
2. **Caffeine**: High-performance in-memory cache. Considered for future optimization.
3. **No caching**: Simplest option. Rejected because it violates NFR 1.1.

**Consequences:**
- ✅ Zero additional infrastructure
- ✅ Simple configuration via @Cacheable annotations
- ✅ Per-instance caching improves response time
- ⚠️ Cache inconsistency across multiple pods (acceptable for read-heavy workloads)
- ⚠️ Cache lost on pod restart (acceptable with database as source of truth)

---

## Data Architecture

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐
│  Customer   │───────│    Order    │
└─────────────┘  1:N  └─────────────┘
                         │    │
                         │    │ 1:N
                         │    └─────────────┐
                         │ 1:1              │
                         ▼                  ▼
                   ┌─────────────┐    ┌─────────────┐
                   │   Invoice   │    │  OrderItem  │
                   └─────────────┘    └─────────────┘
                         │                  │
                         │                  │ N:1
                         │                  ▼
                         │            ┌─────────────┐
                         │            │   Product   │
                         │            └─────────────┘
                         │
                         │ 1:N
                         ▼
                   ┌─────────────┐
                   │   Payment   │
                   └─────────────┘
```

### Database Schema

```sql
-- Customers table
CREATE TABLE customers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(50) NOT NULL,
    banking_details TEXT,
    role VARCHAR(50) NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price DOUBLE NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    customer_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    total_amount DOUBLE NOT NULL DEFAULT 0.0,
    tax_amount DOUBLE NOT NULL DEFAULT 0.0,
    discount_amount DOUBLE NOT NULL DEFAULT 0.0,
    shipping_address TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    invoice_id BIGINT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Order items table
CREATE TABLE order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DOUBLE NOT NULL,
    subtotal DOUBLE NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Invoices table
CREATE TABLE invoices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT UNIQUE NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    billing_name VARCHAR(255) NOT NULL,
    billing_address TEXT NOT NULL,
    subtotal DOUBLE NOT NULL,
    tax_amount DOUBLE NOT NULL DEFAULT 0.0,
    discount_amount DOUBLE NOT NULL DEFAULT 0.0,
    total_amount DOUBLE NOT NULL,
    issue_date TIMESTAMP,
    due_date TIMESTAMP,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Payments table
CREATE TABLE payments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    amount DOUBLE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(255),
    processed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

---

## Order Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ORDER LIFECYCLE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1] Customer Places Order                                               │
│      POST /api/v1/orders                                                 │
│      Status: PENDING                                                     │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [2] Order Staff Reviews                                                 │
│      PUT /api/v1/orders/{id}/review?accept=true                          │
│      Status: ACCEPTED (or REJECTED)                                      │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [3] Accountant Creates Invoice                                          │
│      POST /api/v1/invoices                                               │
│      Status: INVOICED                                                    │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [4] Customer Pays Invoice                                               │
│      POST /api/v1/payments                                               │
│      Payment Status: PROCESSING → COMPLETED                              │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [5] Accountant Verifies Payment                                         │
│      PUT /api/v1/payments/{id}/verify?verified=true                      │
│      Order Status: PAID                                                  │
│      Invoice Status: PAID                                                │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [6] Order Staff Ships Order                                             │
│      PUT /api/v1/orders/{id}/ship                                        │
│      Status: SHIPPED                                                     │
│                                                                          │
│      ↓                                                                   │
│                                                                          │
│  [7] Order Staff Closes Order                                            │
│      PUT /api/v1/orders/{id}/close                                       │
│      Status: CLOSED                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```
