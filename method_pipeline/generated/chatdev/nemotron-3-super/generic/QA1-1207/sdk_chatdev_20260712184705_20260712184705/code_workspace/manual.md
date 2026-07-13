# Order Management System (OMS) Backend - User Manual

## 1. Introduction

This document serves as a user manual for the Order Management System (OMS) backend, a RESTful API built with Python and FastAPI. The OMS backend supports the complete order lifecycle: customer ordering, payment processing, invoicing, shipping, and order closure. It serves three user roles: Customer, Order Staff, and Accountant.

The system is designed as a modular monolith, separating concerns into distinct modules (customer, product, order, payment, invoice) while maintaining a single deployable unit.

## 2. Architecture Overview

### 2.1 Technology Stack
- **Language**: Python 3.12
- **Web Framework**: FastAPI
- **Database**: PostgreSQL (with SQLAlchemy ORM and Alembic for migrations)
- **Caching**: Redis (for product catalog caching)
- **Asynchronous Task Processing**: Celery with Redis broker (for payment processing and invoice generation)
- **API Documentation**: Auto-generated OpenAPI (Swagger UI) available at `/api/v1/openapi.json`

### 2.2 Architectural Style
Modular Monolith: The application is a single deployable unit but is internally divided into modules that encapsulate their own models, services, schemas, and API endpoints. Inter-module communication occurs via well-defined service interfaces.

### 2.3 Key Components
- **API Layer**: FastAPI routes defining REST endpoints.
- **Service Layer**: Business logic encapsulated in service modules (e.g., `order_service.py`, `payment_service.py`).
- **Data Access Layer**: CRUD operations (though the current implementation uses direct SQLAlchemy sessions in services; there is a CRUD layer as well).
- **Database Models**: SQLAlchemy models representing Customers, Products, Orders, OrderItems, Payments, Invoices.
- **External Services**: Redis for caching and Celery broker; PostgreSQL for persistent storage.

## 3. Getting Started

### 3.1 Prerequisites
- Docker Engine and Docker Compose (for containerized deployment)
- OR
- Python 3.12+ and a package manager (uv or pip)
- PostgreSQL and Redis running locally (if not using Docker)

### 3.2 Installation

#### Option A: Using Docker Compose (Recommended)
1. Clone the repository (if not already provided).
2. Navigate to the `oms_backend` directory.
3. Ensure Docker is running.
4. Execute:
   ```bash
   docker-compose up --build
   ```
   This will start three services:
   - `postgres`: PostgreSQL database
   - `redis`: Redis cache and message broker
   - `app`: The FastAPI application

#### Option B: Local Development Setup
1. Install Python 3.12+.
2. Install dependencies using `uv` (or `pip`):
   ```bash
   uv sync   # if using uv
   # or
   pip install -r oms_backend/requirements.txt
   ```
3. Ensure PostgreSQL and Redis are running and accessible.
4. Copy the example environment variables (if any) or set the required environment variables (see `oms_backend/app/core/config.py` for defaults).
5. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the application:
   ```bash
   uvicorn oms_backend.app.main:app --reload
   ```

## 4. Running the Application

### 4.1 With Docker Compose
After running `docker-compose up --build`, the API will be available at `http://localhost:8000`.

### 4.2 Locally
After following the local development setup steps, the API will be available at `http://localhost:8000` (or the host and port specified in the uvicorn command).

## 5. API Documentation

### 5.1 Base URL and Versioning
All API endpoints are prefixed with `/api/v1`. The base URL is `http://localhost:8000/api/v1` when running locally.

### 5.2 Authentication
As per the requirements, no authentication is required for this system. All endpoints are accessible without credentials.

### 5.3 Endpoints Overview

#### Customers
- `GET /customers/` - List customers
- `POST /customers/` - Create a new customer
- `GET /customers/{customer_id}` - Get a specific customer
- `PUT /customers/{customer_id}` - Update a customer
- `DELETE /customers/{customer_id}` - Delete a customer

#### Products
- `GET /products/` - List products
- `POST /products/` - Create a new product
- `GET /products/{product_id}` - Get a specific product
- `PUT /products/{product_id}` - Update a product
- `DELETE /products/{product_id}` - Delete a product

#### Orders
- `GET /orders/` - List orders
- `POST /orders/` - Create a new order (with optional items)
- `GET /orders/{order_id}` - Get a specific order
- `PUT /orders/{order_id}` - Update an order (e.g., change status)
- `DELETE /orders/{order_id}` - Delete an order
- `POST /orders/{order_id}/items/` - Add an item to an order
- `DELETE /orders/{order_id}/items/{item_id}` - Remove an item from an order

#### Invoices
- `GET /invoices/` - List invoices
- `POST /invoices/` - Create a new invoice
- `GET /invoices/{invoice_id}` - Get a specific invoice
- `PUT /invoices/{invoice_id}` - Update an invoice
- `DELETE /invoices/{invoice_id}` - Delete an invoice

#### Payments
- `GET /payments/` - List payments
- `POST /payments/` - Create a new payment
- `GET /payments/{payment_id}` - Get a specific payment
- `PUT /payments/{payment_id}` - Update a payment
- `DELETE /payments/{payment_id}` - Delete a payment

### 5.4 Typical Workflow

The following steps illustrate the typical order lifecycle using the API:

1. **Customer Places Order**
   - Customer (or a frontend on behalf of the customer) calls `POST /orders/` with order details and items.
   - Response: Order object with status `PENDING`.

2. **Order Staff Accepts Order**
   - Order staff calls `PUT /orders/{order_id}` with `{"status": "accepted"}`.
   - Order status changes to `ACCEPTED`.

3. **Accountant Generates Invoice**
   - Accountant calls `POST /invoices/` with `order_id` and `billing_info`.
   - Note: The current implementation does not automatically link the invoice to the order or update order status. For a complete workflow, the accountant may need to also update the order status to `INVOICED` and set the `invoice_id` on the order via `PUT /orders/{order_id}`. (See note below regarding workflow automation.)
   - Alternatively, the system may rely on the order service's `create_invoice_for_order` function, which is not directly exposed via an endpoint. In a production setup, a dedicated endpoint or background process would be used.

4. **Customer Pays Invoice**
   - Customer calls `POST /payments/` with `order_id`, `amount`, and `payment_method`.
   - The payment is processed asynchronously via Celery. Upon successful payment, the payment status becomes `COMPLETED`, the associated invoice status becomes `PAID`, and the order status becomes `PAID`.

5. **Accountant Verifies Payment**
   - Accountant can verify payment by checking the payment status via `GET /payments/{payment_id}` or by checking the order status.

6. **Order Staff Ships Order**
   - Order staff updates the order status to `SHIPPED` via `PUT /orders/{order_id}` with `{"status": "shipped"}`.

7. **Order Staff Closes Order**
   - Order staff updates the order status to `CLOSED` via `PUT /orders/{order_id}` with `{"status": "closed"}`.

> **Note**: The current API exposes CRUD operations for each entity. The workflow steps that involve state transitions (accept, invoice, pay, ship, close) are achieved by updating the respective status fields via the update endpoints. For invoicing, the accountant must create an invoice and then update the order to reference that invoice and set the status to `INVOICED`. Future enhancements could introduce dedicated workflow endpoints to simplify these transitions.

## 6. Testing the API

### 6.1 Swagger UI
When the application is running, interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 6.2 Example curl Commands

#### Create a Product
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/products/' \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Example Product",
    "price": 29.99,
    "currency": "USD"
  }'
```

#### Create a Customer
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/customers/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "John Doe",
    "address": "123 Main St",
    "phone": "555-1234",
    "banking_details": "Bank: XYZ, Account: 123456"
  }'
```

#### Place an Order
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": 1,
    "items": [
      {
        "product_id": 1,
        "quantity": 2,
        "unit_price": 29.99
      }
    ]
  }'
```

#### Accept the Order (Order Staff)
```bash
curl -X 'PUT' \
  'http://localhost:8000/api/v1/orders/1' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "accepted"
  }'
```

#### Create an Invoice (Accountant)
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/invoices/' \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": 1,
    "billing_info": "John Doe, 123 Main St",
    "status": "issued"
  }'
```

#### Make a Payment (Customer)
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/payments/' \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": 1,
    "amount": 59.98,
    "payment_method": "credit_card"
  }'
```

#### Ship the Order (Order Staff)
```bash
curl -X 'PUT' \
  'http://localhost:8000/api/v1/orders/1' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "shipped"
  }'
```

#### Close the Order (Order Staff)
```bash
curl -X 'PUT' \
  'http://localhost:8000/api/v1/orders/1' \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "closed"
  }'
```

## 7. Monitoring and Observability

### 7.1 Logging
The application uses standard Python logging. Logs are output to stdout and can be captured by Docker or your logging system.

### 7.2 Health Check
A simple health check endpoint is available at `/` (root) which returns a JSON message indicating the service is running.

### 7.3 Metrics
Currently, the application does not expose Prometheus metrics. However, the infrastructure can be extended to include Prometheus and Grafana for monitoring system metrics (CPU, memory, request latency, etc.) via the Docker container stats or host monitoring tools.

## 8. Non-Functional Requirements (NFRs) Verification

The system is designed to meet the following non-functional requirements. Below are suggested methods to verify each NFR.

### 8.1 Response Time (NFR 1.1)
- **Requirement**: Core journeys (product search, cart, checkout) must minimize round-trip latency under load.
- **Verification**:
  - Use a load testing tool (e.g., Locust, k6) to simulate concurrent users performing product listing, adding to cart, and checkout.
  - Monitor API response times (average, p95, p99) and ensure they remain within acceptable thresholds (e.g., <200ms for 95% of requests under expected load).
  - Verify that Redis caching is effective for product endpoints by checking cache hit rates.

### 8.2 Concurrency & Resource Utilization (NFR 1.2)
- **Requirement**: The system must exploit available server resources (up to 98GB RAM) with minimal queuing.
- **Verification**:
  - Conduct stress tests with increasing load and observe system resource usage (CPU, memory, disk I/O, network).
  - Ensure that the number of API workers (Uvicorn) and Celery workers scales appropriately with available cores.
  - Monitor queue lengths (Redis for Celery) to ensure tasks are processed promptly and queues do not grow unbounded under load.
  - Verify that database connection pooling is configured and active connections remain within pool limits.

### 8.3 Queue Management (NFR 1.3)
- **Requirement**: Sudden traffic spikes must not crash the system.
- **Verification**:
  - Simulate traffic spikes using a load testing tool and observe that the system remains responsive (does not return 5xx errors due to overload).
  - Check that the Celery broker (Redis) adequately buffers tasks during spikes and that workers process them backlog without failure.
  - Verify that rate limiting (if implemented) or graceful degradation mechanisms prevent system overload.
  - Ensure that error handling and retries are in place for external dependencies (e.g., payment gateways).

## 9. Troubleshooting

### 9.1 Common Issues
- **Database Connection Failures**: Verify that PostgreSQL is running and accessible at the host/port specified in the environment variables or `DATABASE_URL`.
- **Redis Connection Failures**: Verify that Redis is running and accessible.
- **Migration Errors**: Ensure that Alembic is configured correctly and that the database schema matches the expected migration state.
- **Worker Not Processing Tasks**: Check that the Celery worker is running and can connect to the Redis broker.

### 9.2 Logs
- Check the container logs (if using Docker) or the application stdout/stderr for error messages.
- Use `docker-compose logs -f` to follow logs in real-time.

### 9.3 Restarting Services
- With Docker Compose: `docker-compose restart`
- For individual services: `docker-compose restart <service_name>`

## 10. Further Assistance

For additional information, refer to the following documents in the `docs/` directory:
- `NFR_Traceability_Matrix.md`: Details on how non-functional requirements are addressed.
- `Data_Architecture.md`: Overview of the data model and entity relationships.
- `adr/`: Architectural Decision Records explaining key design choices.

If you encounter issues not covered here, please consult the development team or refer to the source code comments.