# Order Management System - Deployment Guide

## Prerequisites

### For Docker Compose (Local Development)
- Docker Desktop or Docker Engine 20.10+
- Docker Compose 2.0+

### For Kubernetes (Production/Staging)
- kubectl 1.25+
- Minikube 1.30+ OR Kind 0.18+
- Helm 3.0+ (optional)

---

## Quick Start

### Option 1: Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f oms-backend

# Access the API
curl http://localhost:8080/api/v1/products

# Access Swagger UI
open http://localhost:8080/swagger-ui.html

# Access H2 Console (development only)
open http://localhost:8080/h2-console
# JDBC URL: jdbc:h2:mem:omsdb
# Username: sa
# Password: (empty)

# Access pgAdmin
open http://localhost:5050
# Email: admin@chatdev.com
# Password: admin

# Stop all services
docker-compose down
```

### Option 2: Kubernetes with Minikube

```bash
# Start minikube
minikube start --memory=4096 --cpus=2

# Build Docker image
minikube image build -t oms-backend:latest .

# Or load image into minikube
docker build -t oms-backend:latest .
minikube image load oms-backend:latest

# Apply Kubernetes manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/rbac.yaml
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl apply -f kubernetes/postgres-service.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=oms-backend -n oms --timeout=120s
kubectl wait --for=condition=ready pod -l app=postgres -n oms --timeout=120s

# Port forward to access the API
kubectl port-forward svc/oms-backend-service 8080:80 -n oms

# Access the API
curl http://localhost:8080/api/v1/products

# Access Swagger UI
open http://localhost:8080/swagger-ui.html

# View logs
kubectl logs -f deployment/oms-backend -n oms

# Check pod status
kubectl get pods -n oms

# Check HPA status
kubectl get hpa -n oms

# Clean up
kubectl delete namespace oms
minikube stop
```

### Option 3: Kubernetes with Kind

```bash
# Create kind cluster
kind create cluster --name oms-cluster

# Build and load Docker image
docker build -t oms-backend:latest .
kind load docker-image oms-backend:latest --name oms-cluster

# Apply Kubernetes manifests
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/pvc.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/rbac.yaml
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl apply -f kubernetes/postgres-service.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=oms-backend -n oms --timeout=120s
kubectl wait --for=condition=ready pod -l app=postgres -n oms --timeout=120s

# Port forward
kubectl port-forward svc/oms-backend-service 8080:80 -n oms

# Access the API
curl http://localhost:8080/api/v1/products

# Clean up
kind delete cluster --name oms-cluster
```

---

## NFR Verification Steps

### NFR 1.1: Response Time

```bash
# Install Apache Bench (if not installed)
# macOS: brew install httpd
# Linux: apt-get install apache2-utils

# Test cached endpoint (should be <50ms)
ab -n 1000 -c 10 http://localhost:8080/api/v1/products/1

# Test non-cached endpoint
ab -n 1000 -c 10 http://localhost:8080/api/v1/orders

# Expected results:
# - Cached endpoints: <50ms average
# - Non-cached endpoints: <200ms average
```

### NFR 1.2: Concurrency & Resource Utilization

```bash
# Check pod resource usage (Kubernetes)
kubectl top pods -n oms

# Check HPA status
kubectl get hpa oms-backend-hpa -n oms

# Watch HPA scaling
kubectl get hpa oms-backend-hpa -n oms -w

# Generate load to trigger scaling
ab -n 10000 -c 50 http://localhost:8080/api/v1/products

# Expected: HPA should scale up when CPU > 70% or Memory > 80%
```

### NFR 1.3: Queue Management (Rate Limiting)

```bash
# Send rapid requests to trigger rate limit
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/v1/products
done

# Expected: After ~100 requests, should see 429 (Too Many Requests) responses

# Check rate limit headers
curl -i http://localhost:8080/api/v1/products | grep -i "x-ratelimit"
```

### NFR 2.1: Localization of Changes

```bash
# Update business rules via ConfigMap (Kubernetes)
kubectl edit configmap oms-config -n oms

# Change tax rate:
# app.business-rules.tax-rate: 0.15  # 15% instead of 10%

# Create a new order and verify tax calculation
curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId":1,"items":[{"productId":1,"quantity":1}]}'

# Verify taxAmount reflects new rate (no code change required)
```

### NFR 2.2: Interface Stability

```bash
# Check OpenAPI spec
curl http://localhost:8080/v3/api-docs | jq '.info.version'

# Verify all v1 endpoints exist
curl http://localhost:8080/v3/api-docs | jq '.paths | keys'

# Expected: All paths should start with /api/v1/
```

### NFR 2.3: Deferred Binding

```bash
# Update feature flags via ConfigMap (Kubernetes)
kubectl edit configmap oms-config -n oms

# Change:
# app.features.recommendations-enabled: false

# Try to access recommendations endpoint (should return 503)
curl -i http://localhost:8080/api/v1/recommendations

# Checkout endpoints should still work
curl http://localhost:8080/api/v1/products
```

### NFR 3.1: Graceful Degradation

```bash
# Enable degradation mode by setting feature flags to false
kubectl edit configmap oms-config -n oms

# Set:
# app.features.analytics-enabled: false
# app.features.recommendations-enabled: false

# Non-essential features should return 503
curl -i http://localhost:8080/api/v1/analytics  # 503

# Core checkout flow should still work
curl http://localhost:8080/api/v1/products     # 200
curl http://localhost:8080/api/v1/orders       # 200
```

### NFR 3.2: Fault Detection & Recovery

```bash
# Check health endpoint
curl http://localhost:8080/actuator/health

# Check liveness probe
curl http://localhost:8080/actuator/health/liveness

# Check readiness probe
curl http://localhost:8080/actuator/health/readiness

# Simulate failure by deleting pod
kubectl delete pod -l app=oms-backend -n oms

# Watch pod restart
kubectl get pods -n oms -w

# Expected: New pod should start within 60 seconds
```

### NFR 3.3: State Preservation

```bash
# Create an order
ORDER_ID=$(curl -X POST http://localhost:8080/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId":1,"items":[{"productId":1,"quantity":1}]}' \
  | jq -r '.id')

echo "Created order: $ORDER_ID"

# Restart pod (Kubernetes)
kubectl delete pod -l app=oms-backend -n oms

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=oms-backend -n oms --timeout=120s

# Port forward again if needed
kubectl port-forward svc/oms-backend-service 8080:80 -n oms &

# Verify order persists
curl http://localhost:8080/api/v1/orders/$ORDER_ID

# Expected: Order should still exist with all data intact
```

---

## API Testing

### Complete Order Workflow Test

```bash
BASE_URL="http://localhost:8080/api/v1"

# 1. Create a customer
CUSTOMER_ID=$(curl -X POST "$BASE_URL/customers" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","address":"123 Main St","phone":"555-1234","role":"CUSTOMER"}' \
  | jq -r '.id')
echo "Customer ID: $CUSTOMER_ID"

# 2. Create a product
PRODUCT_ID=$(curl -X POST "$BASE_URL/products" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Product","description":"A test product","basePrice":99.99,"stockQuantity":100}' \
  | jq -r '.id')
echo "Product ID: $PRODUCT_ID"

# 3. Step 1: Customer places order
ORDER_ID=$(curl -X POST "$BASE_URL/orders" \
  -H "Content-Type: application/json" \
  -d "{\"customerId\":$CUSTOMER_ID,\"items\":[{\"productId\":$PRODUCT_ID,\"quantity\":2}]}" \
  | jq -r '.id')
echo "Order ID: $ORDER_ID"

# 4. Step 2: Order Staff reviews and accepts
curl -X PUT "$BASE_URL/orders/$ORDER_ID/review?accept=true"

# 5. Step 3: Accountant creates invoice
INVOICE_ID=$(curl -X POST "$BASE_URL/invoices" \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":$ORDER_ID,\"billingName\":\"John Doe\",\"billingAddress\":\"123 Main St\"}" \
  | jq -r '.id')
echo "Invoice ID: $INVOICE_ID"

# 6. Step 4: Customer pays invoice
PAYMENT_ID=$(curl -X POST "$BASE_URL/payments" \
  -H "Content-Type: application/json" \
  -d "{\"orderId\":$ORDER_ID,\"amount\":219.98,\"paymentMethod\":\"CREDIT_CARD\"}" \
  | jq -r '.id')
echo "Payment ID: $PAYMENT_ID"

# 7. Step 5: Accountant verifies payment
curl -X PUT "$BASE_URL/payments/$PAYMENT_ID/verify?verified=true"

# 8. Step 6: Order Staff ships order
curl -X PUT "$BASE_URL/orders/$ORDER_ID/ship"

# 9. Step 7: Order Staff closes order
curl -X PUT "$BASE_URL/orders/$ORDER_ID/close"

# Verify final order status
curl "$BASE_URL/orders/$ORDER_ID" | jq '.status'
# Expected: "CLOSED"
```

---

## Monitoring and Observability

### Actuator Endpoints

```bash
# Health check
curl http://localhost:8080/actuator/health

# Application info
curl http://localhost:8080/actuator/info

# Metrics
curl http://localhost:8080/actuator/metrics

# Prometheus metrics (for Prometheus scraping)
curl http://localhost:8080/actuator/prometheus

# Thread dump
curl http://localhost:8080/actuator/threaddump

# Heap dump (if enabled)
curl -o heap.hprof http://localhost:8080/actuator/heapdump
```

### Kubernetes Monitoring

```bash
# View pod metrics
kubectl top pods -n oms

# View deployment status
kubectl get deployment -n oms

# View service endpoints
kubectl get endpoints -n oms

# View events
kubectl get events -n oms --sort-by='.lastTimestamp'

# Port forward to Prometheus (if deployed)
kubectl port-forward svc/prometheus 9090:9090 -n monitoring
```

---

## Troubleshooting

### Common Issues

1. **Pod won't start**
   ```bash
   kubectl describe pod -l app=oms-backend -n oms
   kubectl logs -l app=oms-backend -n oms
   ```

2. **Database connection failures**
   ```bash
   kubectl logs -l app=postgres -n oms
   kubectl exec -it deployment/postgres -n oms -- psql -U oms -d omsdb -c "SELECT 1"
   ```

3. **Rate limiting too aggressive**
   - Edit `RateLimitFilter.java` to adjust `MAX_REQUESTS_PER_SECOND`
   - Or update via environment variable if configured

4. **High memory usage**
   - Adjust JVM heap in `kubernetes/deployment.yaml`:
     ```yaml
     - name: JAVA_OPTS
       value: "-Xms256m -Xmx1g"  # Reduce from 512m-2g
     ```

5. **HPA not scaling**
   ```bash
   kubectl describe hpa oms-backend-hpa -n oms
   # Check metrics-server is running
   kubectl get pods -n kube-system | grep metrics-server
   ```

---

## Production Checklist

- [ ] Update `oms-secrets` with strong passwords
- [ ] Configure proper resource limits based on load testing
- [ ] Enable HTTPS/TLS termination (Ingress or LoadBalancer)
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure alerting on actuator health endpoints
- [ ] Set up backup strategy for PostgreSQL
- [ ] Review and adjust rate limiting thresholds
- [ ] Enable audit logging for compliance
- [ ] Configure network policies for pod-to-pod communication
- [ ] Set up CI/CD pipeline for automated deployments
