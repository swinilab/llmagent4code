# Order Management System (OMS)

A production-grade, backend-only e-commerce Order Management System built with Spring Boot 3.x and Java 17.

## Overview

This OMS backend serves APIs for the complete order workflow:
1. Customer places order
2. Order Staff reviews & accepts
3. Accountant creates invoice
4. Customer pays invoice
5. Accountant verifies payment
6. Order Staff ships paid order
7. Order Staff closes completed order

## Tech Stack

- **Backend:** Spring Boot 3.2.1 (Java 17)
- **Database:** H2 (dev) / PostgreSQL 15 (prod)
- **Containerization:** Docker (multi-stage builds)
- **Orchestration:** Kubernetes (raw manifests)
- **Documentation:** OpenAPI 3.0 (Swagger)

## Quick Start

### Docker Compose (Development)

```bash
# Start all services
docker-compose up -d

# Access API
curl http://localhost:8080/api/v1/products

# Access Swagger UI
open http://localhost:8080/swagger-ui.html
```

### Kubernetes (Production)

```bash
# Deploy to Minikube
minikube start
docker build -t oms-backend:latest .
minikube image load oms-backend:latest

kubectl apply -f kubernetes/

# Port forward
kubectl port-forward svc/oms-backend-service 8080:80 -n oms
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## API Endpoints

### Customers
- `POST /api/v1/customers` - Create customer
- `GET /api/v1/customers/{id}` - Get customer
- `GET /api/v1/customers` - List all customers
- `PUT /api/v1/customers/{id}` - Update customer
- `DELETE /api/v1/customers/{id}` - Delete customer

### Products
- `POST /api/v1/products` - Create product
- `GET /api/v1/products/{id}` - Get product
- `GET /api/v1/products/search?name=...` - Search products
- `GET /api/v1/products` - List all products
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

### Orders
- `POST /api/v1/orders` - Place order (Step 1)
- `GET /api/v1/orders/{id}` - Get order
- `PUT /api/v1/orders/{id}/review?accept=true` - Review order (Step 2)
- `PUT /api/v1/orders/{id}/ship` - Ship order (Step 6)
- `PUT /api/v1/orders/{id}/close` - Close order (Step 7)

### Invoices
- `POST /api/v1/invoices` - Create invoice (Step 3)
- `GET /api/v1/invoices/{id}` - Get invoice
- `PUT /api/v1/invoices/{id}/paid` - Mark as paid

### Payments
- `POST /api/v1/payments` - Create payment (Step 4)
- `PUT /api/v1/payments/{id}/verify?verified=true` - Verify payment (Step 5)

## Non-Functional Requirements

| NFR | Requirement | Implementation |
|-----|-------------|----------------|
| 1.1 | Response Time | Spring Cache, HikariCP pooling |
| 1.2 | Concurrency | HPA autoscaling, JVM tuning |
| 1.3 | Queue Management | RateLimitFilter, request throttling |
| 2.1 | Localization of Changes | Business rules in services, externalized config |
| 2.2 | Interface Stability | Versioned APIs (/api/v1/), OpenAPI spec |
| 2.3 | Deferred Binding | @ConfigurationProperties, ConfigMaps |
| 3.1 | Graceful Degradation | DegradationFilter, feature flags |
| 3.2 | Fault Detection | Resilience4j, health probes |
| 3.3 | State Preservation | PostgreSQL, @Transactional |

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed NFR traceability and ADRs.

## Project Structure

```
src/
├── main/
│   ├── java/com/chatdev/oms/
│   │   ├── OrderManagementSystemApplication.java
│   │   ├── config/          # Cache, Resilience, OpenAPI, Filters
│   │   ├── controller/      # REST Controllers
│   │   ├── dto/             # Request/Response DTOs
│   │   ├── entity/          # JPA Entities
│   │   ├── enums/           # Status Enums
│   │   ├── repository/      # Spring Data Repositories
│   │   └── service/         # Business Logic Services
│   └── resources/
│       └── application.yml  # Configuration
└── test/
    └── java/com/chatdev/oms/
```

## Building

```bash
# Build with Maven
./mvnw clean package

# Run tests
./mvnw test

# Run application
./mvnw spring-boot:run
```

## Testing

```bash
# Run complete workflow test
./test_workflow.sh

# Or use the API testing commands in DEPLOYMENT.md
```

## Monitoring

- Health: `GET /actuator/health`
- Metrics: `GET /actuator/metrics`
- Prometheus: `GET /actuator/prometheus`
- Swagger: `GET /swagger-ui.html`
- OpenAPI: `GET /v3/api-docs`

## License

MIT License - see LICENSE file for details.

## Contact

ChatDev - dev@chatdev.com
