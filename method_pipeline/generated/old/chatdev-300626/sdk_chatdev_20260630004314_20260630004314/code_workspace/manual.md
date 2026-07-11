# Order Management System (OMS) - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [System Overview](#system-overview)
3. [Main Functions](#main-functions)
4. [Environment Setup](#environment-setup)
5. [Running with Docker Compose](#running-with-docker-compose)
6. [Running with Kubernetes](#running-with-kubernetes)
7. [API Usage Guide](#api-usage-guide)
8. [Configuration Reference](#configuration-reference)
9. [Monitoring & Verification](#monitoring--verification)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

The Order Management System (OMS) is a production-grade, backend-only e-commerce platform built with Spring Boot 3.x and Java 17. It serves APIs for the complete order workflow from customer ordering through payment processing, invoicing, shipping, and closure.

This manual provides comprehensive instructions for installing, configuring, and using the OMS backend.

### Key Features

- **Complete Order Workflow**: 7-step process from order placement to closure
- **Multi-Role Support**: Customer, Order Staff, and Accountant roles
- **Production-Ready**: Docker containerization and Kubernetes orchestration
- **Resilient Design**: Circuit breakers, rate limiting, and graceful degradation
- **API Documentation**: OpenAPI 3.0 (Swagger) for all endpoints
- **Externalized Configuration**: Runtime-configurable business rules and feature flags

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│              (Frontend, Mobile, Third-party)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    OMS Backend (Spring Boot)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Customer │ │  Order   │ │  Invoice │ │ Payment  │       │
│  │Controller│ │Controller│ │Controller│ │Controller│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Customer │ │  Order   │ │  Invoice │ │ Payment  │       │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Cross-Cutting Concerns                      │   │
│  │  Cache │ Rate Limit │ Degradation │ Circuit Breaker  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│         (Persistent storage for all entities)                │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Spring Boot 3.2.1 |
| Language | Java 17 |
| Database (Dev) | H2 (in-memory) |
| Database (Prod) | PostgreSQL 15 |
| Containerization | Docker (multi-stage builds) |
| Orchestration | Kubernetes (raw manifests) |
| API Documentation | OpenAPI 3.0 / Swagger |
| Build Tool | Maven |

### Domain Entities

| Entity | Description |
|--------|-------------|
| **Customer** | User account with name, address, phone, banking details, role, and order history |
| **Product** | Items available for order with name, description, base price, currency, and stock |
| **Order** | Customer orders with line items, amounts, status lifecycle, and timestamps |
| **Invoice** | Billing documents linked to orders with billing info, amounts, and due dates |
| **Payment** | Payment transactions with amount, status, method, and transaction ID |

---

## Main Functions

### Order Workflow (7 Steps)

The OMS implements a complete order lifecycle:

```
Step 1: Customer places order
         ↓
Step 2: Order Staff reviews & accepts
         ↓
Step 3: Accountant creates invoice
         ↓
Step 4: Customer pays invoice
         ↓
Step 5: Accountant verifies payment
         ↓
Step 6: Order Staff ships paid order
         ↓
Step 7: Order Staff closes completed order
```

### Order Status Lifecycle

```
PENDING → ACCEPTED → INVOICED → PAID → SHIPPED → COMPLETED
                ↓
            REJECTED
```

| Status | Description | Who Can Transition |
|--------|-------------|-------------------|
| `PENDING` | Order placed, awaiting review | Customer (create) |
| `ACCEPTED` | Order approved by staff | Order Staff |
| `REJECTED` | Order declined by staff | Order Staff |
| `INVOICED` | Invoice created for order | Accountant |
| `PAID` | Payment verified | Accountant |
| `SHIPPED` | Order shipped to customer | Order Staff |
| `COMPLETED` | Order closed successfully | Order Staff |

### User Roles

| Role | Permissions |
|------|-------------|
| **Customer** | Create orders, view own orders, make payments |
| **Order Staff** | Review/accept/reject orders, ship orders, close orders |
| **Accountant** | Create invoices, verify payments |

---

## Environment Setup

### Prerequisites

#### For Docker Compose (Local Development)

| Software | Minimum Version | Installation Link |
|----------|-----------------|-------------------|
| Docker Desktop / Docker Engine | 20.10+ | [docker.com](https://www.docker.com/get-started) |
| Docker Compose | 2.0+ | Included with Docker Desktop |

#### For Kubernetes (Production/Staging)

| Software | Minimum Version | Installation Link |
|----------|-----------------|-------------------|
| kubectl | 1.25+ | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| Minikube | 1.30+ OR Kind 0.18+ | [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/) |
| Helm (optional) | 3.0+ | [helm.sh](https://helm.sh/docs/intro/install/) |

#### For Building from Source

| Software | Minimum Version | Installation Link |
|----------|-----------------|-------------------|
| Java JDK | 17+ | [adoptium.net](https://adoptium.net/) |
| Maven | 3.9+ | [maven.apache.org](https://maven.apache.org/download.cgi) |

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check Kubernetes (if using K8s)
kubectl version --client
minikube version  # or: kind version

# Check Java (for building)
java -version

# Check Maven (for building)
mvn --version
```

### Clone/Access the Project

The project should be in your workspace directory with the following structure:

```
oms/
├── src/                          # Source code
│   ├── main/java/com/chatdev/oms/
│   │   ├── config/               # Configuration classes
│   │   ├── controller/           # REST controllers
│   │   ├── dto/                  # Data transfer objects
│   │   ├── entity/               # JPA entities
│   │   ├── enums/                # Enumerations
│   │   ├── repository/           # Data repositories
│   │   └── service/              # Business logic services
│   └── main/resources/
│       └── application.yml       # Application configuration
├── kubernetes/                   # Kubernetes manifests
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── hpa.yaml
│   ├── namespace.yaml
│   ├── postgres-deployment.yaml
│   ├── postgres-service.yaml
│   ├── pvc.yaml
│   ├── rbac.yaml
│   ├── secret.yaml
│   └── service.yaml
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Multi-stage Docker build
├── pom.xml                       # Maven build configuration
├── README.md                     # Project overview
├── ARCHITECTURE.md               # Architecture documentation
├── DEPLOYMENT.md                 # Deployment guide
└── HELP.md                       # Additional help
```

---

## Running with Docker Compose

### Quick Start

This is the recommended method for local development and testing.

#### Step 1: Start All Services

```bash
# Navigate to the project root directory
cd /path/to/oms

# Start all services (OMS backend + PostgreSQL + pgAdmin)
docker compose up -d
```

#### Step 2: Verify Services Are Running

```bash
# Check container status
docker compose ps

# Expected output:
# NAME             STATUS         PORTS
# oms-backend      Up (healthy)   0.0.0.0:8080->8080/tcp
# oms-postgres     Up (healthy)   5432/tcp
# oms-pgadmin      Up             0.0.0.0:5050->80/tcp
```

#### Step 3: Access the Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8080 | No auth required |
| **Swagger UI** | http://localhost:8080/swagger-ui.html | No auth required |
| **OpenAPI JSON** | http://localhost:8080/v3/api-docs | No auth required |
| **Actuator Health** | http://localhost:8080/actuator/health | No auth required |
| **pgAdmin** | http://localhost:5050 | admin/admin |
| **H2 Console (dev)** | http://localhost:8080/h2-console | sa / (empty) |

#### Step 4: Test the API

```bash
# Test health endpoint
curl http://localhost:8080/actuator/health

# Create a product
curl -X POST http://localhost:8080/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "description": "A test product",
    "basePrice": 99.99,
    "currency": "USD",
    "stockQuantity": 100
  }'

# List all products
curl http://localhost:8080/api/v1/products

# Create a customer
curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "address": "123 Main St, City, Country",
    "phone": "+1-555-123-4567",
    "bankingDetails": "Bank: Test Bank, Account: 123456789",
    "role": "CUSTOMER"
  }'

# Create an order
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": 1,
    "items": [
      {
        "productId": 1,
        "quantity": 2
      }
    ]
  }'
```

#### Step 5: View Logs

```bash
# View all logs
docker compose logs

# View backend logs only
docker compose logs oms-backend

# Follow logs in real-time
docker compose logs -f oms-backend
```

#### Step 6: Stop Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

### Docker Compose Configuration

The `docker-compose.yml` defines three services:

1. **oms-backend**: Spring Boot application
   - Port: 8080
   - Health check: `/actuator/health`
   - Environment: `SPRING_PROFILES_ACTIVE=docker`

2. **postgres**: PostgreSQL 15 database
   - Port: 5432 (internal)
   - Volume: `postgres-data` for persistence
   - Health check: `pg_isready`

3. **pgadmin**: Database management UI
   - Port: 5050
   - Credentials: admin/admin

---

## Running with Kubernetes

### Quick Start for Minikube

#### Step 1: Start Minikube

```bash
# Start Minikube with sufficient resources
minikube start --memory=4096 --cpus=2

# Verify cluster is running
kubectl cluster-info
```

#### Step 2: Build and Load Docker Image

```bash
# Build the Docker image
docker build -t oms-backend:latest .

# Load image into Minikube
minikube image load oms-backend:latest

# Verify image is loaded
minikube image list | grep oms-backend
```

#### Step 3: Create Namespace and Apply Manifests

```bash
# Navigate to kubernetes directory
cd kubernetes

# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (base64 encoded)
kubectl apply -f secret.yaml

# Create ConfigMap
kubectl apply -f configmap.yaml

# Create PVC for PostgreSQL
kubectl apply -f pvc.yaml

# Create RBAC
kubectl apply -f rbac.yaml

# Deploy PostgreSQL
kubectl apply -f postgres-deployment.yaml
kubectl apply -f postgres-service.yaml

# Deploy OMS Backend
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Deploy HPA (Horizontal Pod Autoscaler)
kubectl apply -f hpa.yaml
```

#### Step 4: Verify Deployment

```bash
# Check all resources in oms namespace
kubectl get all -n oms

# Expected output:
# NAME                              READY   STATUS    RESTARTS   AGE
# pod/oms-backend-xxxxx-xxxxx       1/1     Running   0          2m
# pod/oms-backend-xxxxx-xxxxx       1/1     Running   0          2m
# pod/postgres-xxxxx-xxxxx          1/1     Running   0          3m

# NAME                    TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
# service/oms-backend     ClusterIP   10.96.xxx.xxx    <none>        80/TCP     2m
# service/postgres-svc    ClusterIP   10.96.xxx.xxx    <none>        5432/TCP   3m

# NAME                          READY   MINPODS   MAXPODS   REPLICAS   AGE
# horizontalpodautoscaler/oms-backend-hpa   0/0     2         10        0          1m
```

#### Step 5: Access the Application

```bash
# Option 1: Port forwarding (recommended for testing)
kubectl port-forward svc/oms-backend -n oms 8080:80

# Then access: http://localhost:8080

# Option 2: Minikube service
minikube service oms-backend -n oms --url

# Option 3: Enable ingress (for production-like setup)
minikube addons enable ingress
```

#### Step 6: Monitor and Scale

```bash
# View pod metrics (requires metrics-server)
kubectl top pods -n oms

# Watch HPA scaling
kubectl get hpa -n oms -w

# View logs
kubectl logs -f deployment/oms-backend -n oms

# Check events
kubectl get events -n oms --sort-by='.lastTimestamp'
```

#### Step 7: Clean Up

```bash
# Delete entire namespace
kubectl delete namespace oms

# Or delete individual resources
kubectl delete -f kubernetes/
```

### Quick Start for Kind

```bash
# Create Kind cluster
kind create cluster --name oms-cluster

# Load Docker image
docker build -t oms-backend:latest .
kind load docker-image oms-backend:latest --name oms-cluster

# Apply manifests (same as Minikube)
kubectl apply -f kubernetes/

# Port forward
kubectl port-forward svc/oms-backend -n oms 8080:80
```

### Kubernetes Resources Overview

| Resource | File | Purpose |
|----------|------|---------|
| **Namespace** | `namespace.yaml` | Isolates OMS resources |
| **ConfigMap** | `configmap.yaml` | Externalized configuration (NFR 2.3) |
| **Secret** | `secret.yaml` | Sensitive data (passwords) |
| **PVC** | `pvc.yaml` | Persistent storage for PostgreSQL |
| **RBAC** | `rbac.yaml` | Service account and permissions |
| **PostgreSQL Deployment** | `postgres-deployment.yaml` | Database server |
| **PostgreSQL Service** | `postgres-service.yaml` | Database network access |
| **Backend Deployment** | `deployment.yaml` | OMS application pods |
| **Backend Service** | `service.yaml` | Application network access |
| **HPA** | `hpa.yaml` | Auto-scaling (NFR 1.2) |

---

## API Usage Guide

### Base URL

| Environment | Base URL |
|-------------|----------|
| Docker Compose | http://localhost:8080/api/v1 |
| Kubernetes (port-forward) | http://localhost:8080/api/v1 |
| Kubernetes (service) | http://oms-backend.oms.svc.cluster.local/api/v1 |

### API Versioning

All endpoints use versioned paths (`/api/v1/`) to ensure interface stability (NFR 2.2). Future versions will use `/api/v2/`, etc.

### Complete API Reference

#### Products API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/products` | Create a new product |
| GET | `/api/v1/products` | List all products |
| GET | `/api/v1/products/{id}` | Get product by ID |
| PUT | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Delete product |

**Example: Create Product**

```bash
curl -X POST http://localhost:8080/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Widget",
    "description": "High-quality widget for all your needs",
    "basePrice": 149.99,
    "currency": "USD",
    "stockQuantity": 500
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Premium Widget",
  "description": "High-quality widget for all your needs",
  "basePrice": 149.99,
  "currency": "USD",
  "stockQuantity": 500,
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:30:00"
}
```

#### Customers API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create a new customer |
| GET | `/api/v1/customers` | List all customers |
| GET | `/api/v1/customers/{id}` | Get customer by ID |
| PUT | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |

**Example: Create Customer**

```bash
curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "address": "456 Oak Avenue, Springfield, USA",
    "phone": "+1-555-987-6543",
    "bankingDetails": "Bank: Global Bank, Account: 987654321",
    "role": "CUSTOMER"
  }'
```

**Valid Roles:** `CUSTOMER`, `ORDER_STAFF`, `ACCOUNTANT`

#### Orders API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/orders` | Place a new order (Step 1) |
| GET | `/api/v1/orders` | List all orders |
| GET | `/api/v1/orders/{id}` | Get order by ID |
| PUT | `/api/v1/orders/{id}/review` | Review/accept/reject order (Step 2) |
| PUT | `/api/v1/orders/{id}/ship` | Ship order (Step 6) |
| PUT | `/api/v1/orders/{id}/close` | Close order (Step 7) |

**Example: Place Order**

```bash
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerId": 1,
    "items": [
      {
        "productId": 1,
        "quantity": 2
      },
      {
        "productId": 2,
        "quantity": 1
      }
    ]
  }'
```

**Example: Review Order (Accept)**

```bash
curl -X PUT http://localhost:8080/api/v1/orders/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "accepted": true,
    "rejectionReason": null
  }'
```

**Example: Review Order (Reject)**

```bash
curl -X PUT http://localhost:8080/api/v1/orders/1/review \
  -H "Content-Type: application/json" \
  -d '{
    "accepted": false,
    "rejectionReason": "Insufficient stock"
  }'
```

#### Invoices API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/invoices` | Create invoice for order (Step 3) |
| GET | `/api/v1/invoices` | List all invoices |
| GET | `/api/v1/invoices/{id}` | Get invoice by ID |
| GET | `/api/v1/invoices/order/{orderId}` | Get invoice by order ID |

**Example: Create Invoice**

```bash
curl -X POST http://localhost:8080/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": 1,
    "billingName": "Jane Smith",
    "billingAddress": "456 Oak Avenue, Springfield, USA"
  }'
```

#### Payments API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payments` | Create payment (Step 4) |
| GET | `/api/v1/payments` | List all payments |
| GET | `/api/v1/payments/{id}` | Get payment by ID |
| PUT | `/api/v1/payments/{id}/verify` | Verify payment (Step 5) |

**Example: Create Payment**

```bash
curl -X POST http://localhost:8080/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": 1,
    "amount": 449.97,
    "paymentMethod": "CREDIT_CARD",
    "transactionId": "TXN-123456789"
  }'
```

**Example: Verify Payment**

```bash
curl -X PUT http://localhost:8080/api/v1/payments/1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "verified": true
  }'
```

### Complete Workflow Example

Here's a complete order workflow from start to finish:

```bash
# Step 0: Create a product
PRODUCT_ID=$(curl -X POST http://localhost:8080/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Widget","description":"Test","basePrice":100.00,"currency":"USD","stockQuantity":50}' \
  | jq '.id')

# Step 0: Create a customer
CUSTOMER_ID=$(curl -X POST http://localhost:8080/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"123 Main St","phone":"+1-555-1234","bankingDetails":"Bank123","role":"CUSTOMER"}' \
  | jq '.id')

# Step 1: Customer places order
ORDER_ID=$(curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{\"customerId\":$CUSTOMER_ID,\"items\":[{\"productId\":$PRODUCT_ID,\"quantity\":2}]}" \
  | jq '.id')

echo "Order created: $ORDER_ID"

# Step 2: Order Staff reviews & accepts
curl -X PUT http://localhost:8080/api/v1/orders/$ORDER_ID/review \
  -H "Content-Type: application/json" \
  -d '{"accepted":true}'

# Step 3: Accountant creates invoice
INVOICE_ID=$(curl -X POST http://localhost:8080/api/v1/invoices \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":$ORDER_ID,\"billingName\":\"John Doe\",\"billingAddress\":\"123 Main St\"}" \
  | jq '.id')

# Step 4: Customer pays invoice
PAYMENT_ID=$(curl -X POST http://localhost:8080/api/v1/payments \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":$ORDER_ID,\"amount\":220.00,\"paymentMethod\":\"CREDIT_CARD\",\"transactionId\":\"TXN-001\"}" \
  | jq '.id')

# Step 5: Accountant verifies payment
curl -X PUT http://localhost:8080/api/v1/payments/$PAYMENT_ID/verify \
  -H "Content-Type: application/json" \
  -d '{"verified":true}'

# Step 6: Order Staff ships order
curl -X PUT http://localhost:8080/api/v1/orders/$ORDER_ID/ship

# Step 7: Order Staff closes order
curl -X PUT http://localhost:8080/api/v1/orders/$ORDER_ID/close

# Verify final order status
curl http://localhost:8080/api/v1/orders/$ORDER_ID | jq '.status'
# Expected: "COMPLETED"
```

### Error Handling

The API returns standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 404 | Not Found |
| 409 | Conflict (e.g., duplicate invoice) |
| 422 | Unprocessable Entity (business rule violation) |
| 429 | Too Many Requests (rate limit exceeded) |
| 503 | Service Unavailable (degradation mode) |

**Error Response Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "status": 400,
  "error": "Bad Request",
  "message": "Validation failed",
  "details": [
    {
      "field": "name",
      "rejectedValue": null,
      "message": "must not be null"
    }
  ]
}
```

---

## Configuration Reference

### Application Properties

All configuration is externalized via `application.yml` and can be overridden via environment variables or ConfigMaps (NFR 2.3).

#### Feature Flags (NFR 3.1 - Graceful Degradation)

```yaml
app:
  features:
    recommendations-enabled: true    # Enable/disable recommendations
    analytics-enabled: true          # Enable/disable analytics
    caching-enabled: true            # Enable/disable caching
```

#### Business Rules (NFR 2.1 - Localization of Changes)

```yaml
app:
  business-rules:
    tax-rate: 0.10                          # 10% tax
    bulk-discount-threshold: 1000.0         # Orders > $1000 get discount
    bulk-discount-rate: 0.05                # 5% bulk discount
    invoice-due-date-offset-days: 30        # Invoice due in 30 days
```

#### Performance Settings (NFR 1.1, NFR 1.2)

```yaml
app:
  performance:
    cache-ttl-seconds: 300                  # Cache TTL
    max-requests-per-second: 100            # Rate limit
    circuit-breaker-failure-threshold: 5    # Circuit breaker threshold
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SPRING_PROFILES_ACTIVE` | Active profile | `default` |
| `SPRING_DATASOURCE_URL` | Database JDBC URL | `jdbc:h2:mem:omsdb` |
| `SPRING_DATASOURCE_USERNAME` | Database username | `sa` |
| `SPRING_DATASOURCE_PASSWORD` | Database password | (empty) |
| `JAVA_OPTS` | JVM options | `-Xms512m -Xmx2g` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `omspassword` |

### Kubernetes ConfigMap

The ConfigMap (`kubernetes/configmap.yaml`) contains all runtime configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: oms-config
  namespace: oms
data:
  application.yml: |
    app:
      version: 1.0.0
      features:
        recommendations-enabled: true
        analytics-enabled: true
        caching-enabled: true
      business-rules:
        tax-rate: 0.10
        bulk-discount-threshold: 1000.0
        bulk-discount-rate: 0.05
        invoice-due-date-offset-days: 30
```

**To update configuration without restart:**

```bash
# Edit ConfigMap
kubectl edit configmap oms-config -n oms

# Or apply updated ConfigMap
kubectl apply -f kubernetes/configmap.yaml

# Note: Some properties require application restart
```

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: oms-secrets
  namespace: oms
type: Opaque
stringData:
  POSTGRES_PASSWORD: omspassword
```

**To update secrets:**

```bash
# Delete and recreate secret
kubectl delete secret oms-secrets -n oms
kubectl apply -f kubernetes/secret.yaml

# Or use kubectl create secret
kubectl create secret generic oms-secrets \
  --from-literal=POSTGRES_PASSWORD=newpassword \
  -n oms \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: oms-backend-hpa
  namespace: oms
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          averageUtilization: 80
```

**Scaling behavior:**
- Scale up when CPU > 70% or memory > 80%
- Scale down after 5 minutes of low utilization
- Maximum 100% increase per 15 seconds (scale up)
- Maximum 10% decrease per minute (scale down)

---

## Monitoring & Verification

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `/actuator/health` | Overall health status |
| `/actuator/health/liveness` | Liveness probe (K8s) |
| `/actuator/health/readiness` | Readiness probe (K8s) |
| `/actuator/metrics` | Application metrics |
| `/actuator/info` | Application info |

### Verify NFR Compliance

#### NFR 1.1: Response Time

```bash
# Install Apache Bench (if not installed)
# Ubuntu: apt-get install apache2-utils
# macOS: brew install apache-bench

# Test response time (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8080/api/v1/products

# Expected: Most requests < 100ms for cached endpoints

# Check metrics
curl http://localhost:8080/actuator/metrics/http.server.requests
```

#### NFR 1.2: Concurrency & Resource Utilization

```bash
# Kubernetes: Monitor pod resources
kubectl top pods -n oms

# Watch HPA scaling
kubectl get hpa oms-backend-hpa -n oms -w

# Expected: HPA scales between 2-10 replicas based on CPU/memory

# Check JVM metrics
curl http://localhost:8080/actuator/metrics/jvm.memory.used
```

#### NFR 1.3: Queue Management (Rate Limiting)

```bash
# Send 110+ rapid requests
for i in {1..110}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/v1/products
done

# Expected: Some requests return 429 (Too Many Requests)

# Check rate limit headers
curl -I http://localhost:8080/api/v1/products
# Look for: X-RateLimit-Limit, X-RateLimit-Remaining
```

#### NFR 2.1: Localization of Changes

```bash
# Update tax rate in ConfigMap
kubectl edit configmap oms-config -n oms
# Change: tax-rate: 0.10 → tax-rate: 0.15

# Create new order and verify tax calculation
# Tax should be 15% without code change
```

#### NFR 2.2: Interface Stability

```bash
# Check OpenAPI spec
curl http://localhost:8080/v3/api-docs | jq '.info.version'

# Access Swagger UI
open http://localhost:8080/swagger-ui.html

# Verify all v1 paths are present and stable
```

#### NFR 2.3: Deferred Binding

```bash
# Update feature flag in ConfigMap
kubectl edit configmap oms-config -n oms
# Change: recommendations-enabled: true → false

# Test recommendations endpoint (should return 503)
curl -I http://localhost:8080/api/v1/recommendations
# Expected: 503 Service Unavailable

# Verify checkout still works
curl http://localhost:8080/api/v1/products
# Expected: 200 OK
```

#### NFR 3.1: Graceful Degradation

```bash
# Set degradation mode
kubectl edit configmap oms-config -n oms
# Set: recommendations-enabled: false, analytics-enabled: false

# Verify non-essential features are disabled
curl http://localhost:8080/api/v1/recommendations
# Expected: 503

# Verify essential features still work
curl http://localhost:8080/api/v1/orders
# Expected: 200
```

#### NFR 3.2: Fault Detection & Recovery

```bash
# Delete pod (simulate failure)
kubectl delete pod -l app=oms-backend -n oms

# Watch automatic restart
kubectl get pods -n oms -w

# Expected: New pod created within 30 seconds

# Check circuit breaker metrics
curl http://localhost:8080/actuator/metrics/resilience4j.circuitbreaker.state
```

#### NFR 3.3: State Preservation

```bash
# Create an order
ORDER_ID=$(curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId":1,"items":[{"productId":1,"quantity":1}]}' \
  | jq '.id')

# Restart all pods
kubectl rollout restart deployment/oms-backend -n oms

# Wait for pods to be ready
kubectl rollout status deployment/oms-backend -n oms

# Verify order persists
curl http://localhost:8080/api/v1/orders/$ORDER_ID
# Expected: Order data returned (not 404)
```

### Logs and Debugging

```bash
# Docker Compose logs
docker compose logs oms-backend

# Kubernetes logs
kubectl logs -f deployment/oms-backend -n oms

# Kubernetes logs with grep
kubectl logs deployment/oms-backend -n oms | grep -i error

# Kubernetes events
kubectl get events -n oms --sort-by='.lastTimestamp'
```

### Database Access

#### PostgreSQL (Production)

```bash
# Docker Compose
docker compose exec postgres psql -U oms -d omsdb

# Kubernetes
kubectl exec -it deployment/postgres -n oms -- psql -U oms -d omsdb

# Useful queries
\dt                    # List tables
SELECT * FROM orders;  # View orders
SELECT * FROM customers;  # View customers
```

#### H2 Console (Development)

Access: http://localhost:8080/h2-console

| Field | Value |
|-------|-------|
| JDBC URL | `jdbc:h2:mem:omsdb` |
| Username | `sa` |
| Password | (leave empty) |

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms:** Container exits immediately, health check fails

**Solutions:**

```bash
# Check logs
docker compose logs oms-backend
# or
kubectl logs deployment/oms-backend -n oms

# Common causes:
# - Database not ready: Wait for postgres health check
# - Port already in use: Change port in docker-compose.yml
# - Out of memory: Increase JAVA_OPTS -Xmx value

# Verify database is healthy
docker compose ps postgres
# or
kubectl get pods -n oms | grep postgres
```

#### 2. Database Connection Errors

**Symptoms:** `Connection refused`, `Timeout waiting for idle object`

**Solutions:**

```bash
# Check database is running
docker compose ps postgres

# Check network connectivity
docker compose exec oms-backend ping postgres

# Verify credentials
docker compose exec oms-backend env | grep SPRING_DATASOURCE

# For Kubernetes, check service discovery
kubectl get svc -n oms
kubectl exec -it deployment/oms-backend -n oms -- nslookup postgres-service
```

#### 3. Rate Limiting Too Aggressive

**Symptoms:** 429 errors during normal usage

**Solutions:**

```bash
# Increase rate limit in ConfigMap
kubectl edit configmap oms-config -n oms
# Change: max-requests-per-second: 100 → 200

# Or via environment variable
export APP_PERFORMANCE_MAX_REQUESTS_PER_SECOND=200
```

#### 4. High Memory Usage

**Symptoms:** OOMKilled, pods restarting

**Solutions:**

```bash
# Increase memory limits in deployment
kubectl edit deployment oms-backend -n oms
# Update: resources.limits.memory: 2Gi → 4Gi

# Tune JVM options
# Update JAVA_OPTS: -Xms512m -Xmx2g → -Xms1g -Xmx3g
```

#### 5. Slow Response Times

**Symptoms:** Requests taking > 1 second

**Solutions:**

```bash
# Check if caching is enabled
curl http://localhost:8080/actuator/metrics | grep cache

# Enable caching in ConfigMap
app:
  features:
    caching-enabled: true

# Check database performance
kubectl exec -it deployment/postgres -n oms -- pg_stat_activity

# Scale up replicas
kubectl scale deployment oms-backend --replicas=5 -n oms
```

#### 6. HPA Not Scaling

**Symptoms:** Pod count stays constant under load

**Solutions:**

```bash
# Check if metrics-server is running
kubectl get pods -n kube-system | grep metrics-server

# Install metrics-server (Minikube)
minikube addons enable metrics-server

# Check HPA status
kubectl get hpa oms-backend-hpa -n oms

# Verify current metrics
kubectl top pods -n oms

# Check if load is sufficient to trigger scaling
# (CPU > 70% or memory > 80%)
```

#### 7. Circuit Breaker Open

**Symptoms:** 503 errors, circuit breaker metrics show OPEN state

**Solutions:**

```bash
# Check circuit breaker state
curl http://localhost:8080/actuator/metrics/resilience4j.circuitbreaker.state

# Wait for automatic recovery (default: 30 seconds)

# Or reduce failure threshold
app:
  performance:
    circuit-breaker-failure-threshold: 10
```

### Getting Help

1. **Check Documentation:**
   - `README.md` - Project overview
   - `ARCHITECTURE.md` - Architecture decisions and NFR traceability
   - `DEPLOYMENT.md` - Detailed deployment instructions
   - `HELP.md` - Additional help and references

2. **Check Logs:**
   ```bash
   docker compose logs oms-backend
   # or
   kubectl logs -f deployment/oms-backend -n oms
   ```

3. **Check Health:**
   ```bash
   curl http://localhost:8080/actuator/health
   ```

4. **Access Swagger UI:**
   ```
   http://localhost:8080/swagger-ui.html
   ```

5. **Contact Support:**
   - Email: dev@chatdev.com
   - Repository: Check project documentation

---

## Appendix

### Quick Reference Commands

```bash
# Docker Compose
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose logs -f            # Follow logs
docker compose ps                 # Check status

# Kubernetes
kubectl apply -f kubernetes/      # Deploy all resources
kubectl get all -n oms            # Check resources
kubectl logs -f deployment/oms-backend -n oms  # View logs
kubectl port-forward svc/oms-backend -n oms 8080:80  # Port forward

# API Testing
curl http://localhost:8080/actuator/health           # Health check
curl http://localhost:8080/swagger-ui.html           # Swagger UI
curl http://localhost:8080/api/v1/products           # List products
curl http://localhost:8080/api/v1/orders             # List orders

# Build
./mvnw clean package -DskipTests    # Build JAR
docker build -t oms-backend:latest .  # Build Docker image
```

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| pgAdmin | admin | admin |
| PostgreSQL (oms) | oms | omspassword |
| H2 Console | sa | (empty) |

### Port Mapping

| Service | Internal Port | External Port |
|---------|---------------|---------------|
| OMS Backend | 8080 | 8080 |
| PostgreSQL | 5432 | (internal only) |
| pgAdmin | 80 | 5050 |

### File Locations

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development orchestration |
| `Dockerfile` | Container image build instructions |
| `pom.xml` | Maven dependencies and build config |
| `src/main/resources/application.yml` | Application configuration |
| `kubernetes/*.yaml` | Kubernetes manifests |
| `src/main/java/com/chatdev/oms/` | Source code |

---

**Document Version:** 1.0.0  
**Last Updated:** 2024  
**Maintained by:** ChatDev Product Team
