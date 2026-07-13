# Order Management System (OMS) Backend - User Manual

## 1. Introduction

This manual provides instructions on how to install, configure, and use the Order Management System (OMS) backend. The OMS is a production-grade backend-only system that manages the complete workflow of customer ordering, payment processing, invoicing, shipping, and order closure.

This document serves as the primary user manual and references all supporting documentation including architecture decisions, data models, API specifications, and non-functional requirement verification.

## 2. Features

- RESTful API with OpenAPI 3.0 documentation
- Role-based access (Customer, Order Staff, Accountant)
- Complete order lifecycle management
- Payment processing simulation
- Invoice generation
- Shipping tracking
- Order closure
- Designed for scalability and maintainability
- Implements Non-Functional Requirements (NFRs):
  - Graceful Degradation
  - Fault Detection and Recovery
  - State Preservation

## 3. Documentation Overview

This user manual is complemented by several detailed technical documents located in the `docs/` directory:

- **[NFR Traceability Matrix](docs/NFR_Traceability_Matrix.md)**: Maps non-functional requirements to architectural components and verification methods
- **Architecture Decision Records (ADRs)**:
  - [ADR 001: Architectural Style](docs/ADR-001-Architectural-Style.md)
  - [ADR 002: Database Choice](docs/ADR-002-Database-Choice.md)
  - [ADR 003: Dependency Injection](docs/ADR-003-Dependency-Injection.md)
- **[Data Architecture](docs/Data_Architecture.md)**: Detailed database schema and design decisions
- **[Shared Domain Models](docs/Shared_Domain_Models.md)**: API request/response models used throughout the system

## 4. Architecture Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: SQLite (development), configurable to PostgreSQL (production)
- **Dependency Injection**: FastAPI Depends
- **API Versioning**: Path-based (`/v1/`)

## 5. Installation and Setup

### Prerequisites
- Python 3.11+
- Git
- Docker (optional, for containerized deployment)

### Option 1: Local Installation (Without Docker)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oms-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (optional):
   ```bash
   export DATABASE_URL="sqlite:///./test.db"
   export DEBUG="True"
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Access the API at `http://localhost:8000`
   - Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
   - Alternative API documentation (ReDoc): `http://localhost:8000/redoc`
   - OpenAPI JSON: `http://localhost:8000/openapi.json`

### Option 2: Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t oms-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --name oms-app oms-backend
   ```

3. Access the API at `http://localhost:8000` (same documentation URLs as above).

## 6. Using the System: Workflow Guide

The OMS supports the following workflow:

1. **Customer places an order**
2. **Order Staff reviews and accepts the order**
3. **Accountant creates an invoice for the accepted order**
4. **Customer pays the invoice**
5. **Accountant verifies the payment**
6. **Order Staff ships the paid order**
7. **Order Staff closes the completed order**

Below are example API calls (using `curl`) to demonstrate each step. Assume we have a SQLite database at `./test.db`.

### Step 1: Customer Places an Order

First, we need a customer and some products. Let's create a customer and a product.

**Create a Customer (role: Customer):**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "John Doe",
    "address": "123 Main St",
    "phone": "555-1234",
    "banking_details": "Bank Account: 12345678",
    "role": "Customer",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "id": 1,
  "name": "John Doe",
  "address": "123 Main St",
  "phone": "555-1234",
  "banking_details": "Bank Account: 12345678",
  "role": "Customer",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Create a Product:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/products/' \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Laptop",
    "base_price": 150000,
    "currency": "USD"
  }'
```

Response:
```json
{
  "id": 1,
  "description": "Laptop",
  "base_price": 150000,
  "currency": "USD",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Create an Order:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": 1,
    "status": "pending",
    "total_amount": 150000,
    "items": [
      {
        "product_id": 1,
        "quantity": 1,
        "unit_price": 150000,
        "total_price": 150000
      }
    ]
  }'
```

Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "pending",
  "total_amount": 150000,
  "invoice_id": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### Step 2: Order Staff Reviews and Accepts the Order

Create an Order Staff user:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Jane Staff",
    "address": "456 Office St",
    "phone": "555-5678",
    "banking_details": "Bank Account: 87654321",
    "role": "Order Staff",
    "password": "staffpassword"
  }'
```

Accept the order (assuming order ID is 1):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/accept' \
  -H 'Content-Type: application/json'
```

Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "accepted",
  "total_amount": 150000,
  "invoice_id": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:01"
}
```

### Step 3: Accountant Creates an Invoice

Create an Accountant user:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Alice Accountant",
    "address": "789 Finance Ave",
    "phone": "555-9012",
    "banking_details": "Bank Account: 11223344",
    "role": "Accountant",
    "password": "accountantpassword"
  }'
```

Create invoice for order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/invoice' \
  -H 'Content-Type: application/json' \
  -d '{
    "billing_info": "John Doe, 123 Main St"
  }'
```

Response:
```json
{
  "id": 1,
  "order_id": 1,
  "billing_info": "John Doe, 123 Main St",
  "amount": 150000,
  "issue_date": "2024-01-01T00:00:01",
  "due_date": "2024-01-15T00:00:00",
  "status": "issued",
  "created_at": "2024-01-01T00:00:01",
  "updated_at": "2024-01-01T00:00:01"
}
```

### Step 4: Customer Pays the Invoice

Simulate payment (amount in cents):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/pay' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 150000,
    "method": "Credit Card"
  }'
```

Response:
```json
{
  "id": 1,
  "order_id": 1,
  "amount": 150000,
  "timestamp": "2024-01-01T00:00:02",
  "status": "pending",
  "method": "Credit Card"
}
```

### Step 5: Accountant Verifies the Payment

Verify payment (payment ID is 1):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/payments/1/verify' \
  -H 'Content-Type: application/json'
```

Response:
```json
{
  "id": 1,
  "order_id": 1,
  "amount": 150000,
  "timestamp": "2024-01-01T00:00:02",
  "status": "verified",
  "method": "Credit Card"
}
```

### Step 6: Order Staff Ships the Paid Order

Ship order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/ship' \
  -H 'Content-Type: application/json'
```

Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "shipped",
  "total_amount": 150000,
  "invoice_id": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:03"
}
```

### Step 7: Order Staff Closes the Completed Order

Close order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/close' \
  -H 'Content-Type: application/json'
```

Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "closed",
  "total_amount": 150000,
  "invoice_id": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:04"
}
```

## 7. Verifying Non-Functional Requirements (NFRs)

For detailed verification procedures, refer to the [NFR Traceability Matrix](docs/NFR_Traceability_Matrix.md). Below is a summary of how to observe each NFR in action:

### NFR 2.1: Graceful Degradation
**Objective**: Under extreme resource contention, the system must degrade non-essential features to ensure core checkout functionality remains available.

**Verification Method**:
1. Use a load testing tool (e.g., Locust) to simulate high traffic on non-critical endpoints (e.g., `/api/v1/products`, `/api/v1/users`)
2. Monitor critical endpoints (`/api/v1/orders`, `/api/v1/payments`, `/api/v1/invoices`)
3. Under extreme load, non-critical endpoints may return 503, while critical endpoints remain responsive (2xx/3xx)
4. Check middleware logs for overload activation

### NFR 2.2: Fault Detection and Recovery
**Objective**: The application must detect internal component failures and automatically attempt to recover or reconnect, minimizing user-facing errors.

**Verification Method**:
1. Simulate database failure (e.g., stop the Docker container for PostgreSQL or rename the SQLite file)
2. Observe logs for connection errors and retry attempts
3. Restore the database and verify the application reconnects and continues without manual intervention
4. Simulate payment gateway failure and verify retry attempts
5. Check application logs for retry attempts and recovery messages

### NFR 2.3: State Preservation
**Objective**: In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.

**Verification Method**:
1. Create an order and move it to an intermediate state (e.g., after acceptance)
2. Kill the application process (Ctrl+C or kill command)
3. Restart the application
4. Retrieve the order and verify its state is preserved and can proceed to the next step
5. Check that no committed data is lost (verify via database queries)

## 8. Troubleshooting

- **Database Connection Errors**: Check the `DATABASE_URL` environment variable and ensure the database is accessible.
- **Port Already in Use**: Change the port in the `uvicorn` command or stop the existing process on port 8000.
- **Module Not Found Errors**: Ensure you are in the virtual environment and have installed dependencies.
- **Docker Issues**: Verify Docker is running and you have sufficient permissions to execute Docker commands.

## 9. API Documentation

Interactive API documentation is available when the application is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Specification: http://localhost:8000/openapi.json

## 10. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 11. Support

For any issues or questions, please refer to the project documentation or contact the development team.

---
*Last updated: $(date)*

## 1. Introduction

This manual provides instructions on how to install, configure, and use the Order Management System (OMS) backend. The OMS is a production-grade backend-only system that manages the complete workflow of customer ordering, payment processing, invoicing, shipping, and order closure.

## 2. Features

- RESTful API with OpenAPI 3.0 documentation
- Role-based access (Customer, Order Staff, Accountant)
- Complete order lifecycle management
- Payment processing simulation
- Invoice generation
- Shipping tracking
- Order closure
- Designed for scalability and maintainability
- Implements Non-Functional Requirements (NFRs):
  - Graceful Degradation
  - Fault Detection and Recovery
  - State Preservation

## 3. Architecture Overview

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: SQLite (development), configurable to PostgreSQL (production)
- **Dependency Injection**: FastAPI Depends
- **API Versioning**: Path-based (`/v1/`)

## 4. Installation and Setup

### Prerequisites
- Python 3.11+
- Git
- Docker (optional, for containerized deployment)

### Option 1: Local Installation (Without Docker)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oms-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (optional):
   ```bash
   export DATABASE_URL="sqlite:///./test.db"
   export DEBUG="True"
   ```

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

6. Access the API at `http://localhost:8000`
   - Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
   - Alternative API documentation (ReDoc): `http://localhost:8000/redoc`
   - OpenAPI JSON: `http://localhost:8000/openapi.json`

### Option 2: Docker Installation

1. Build the Docker image:
   ```bash
   docker build -t oms-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --name oms-app oms-backend
   ```

3. Access the API at `http://localhost:8000` (same documentation URLs as above).

## 5. Running the Application

After starting the application (via either method), the server will be available at `http://localhost:8000`. The API documentation provides an interactive interface to test all endpoints.

## 6. Using the System: Workflow Guide

The OMS supports the following workflow:

1. **Customer places an order**
2. **Order Staff reviews and accepts the order**
3. **Accountant creates an invoice for the accepted order**
4. **Customer pays the invoice**
5. **Accountant verifies the payment**
6. **Order Staff ships the paid order**
7. **Order Staff closes the completed order**

Below are example API calls (using `curl`) to demonstrate each step. Assume we have a SQLite database at `./test.db`.

### Step 1: Customer Places an Order

First, we need a customer and some products. Let's create a customer and a product.

**Create a Customer (role: Customer):**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "John Doe",
    "address": "123 Main St",
    "phone": "555-1234",
    "banking_details": "Bank Account: 12345678",
    "role": "Customer",
    "password": "securepassword123"
  }'
```
Response:
```json
{
  "id": 1,
  "name": "John Doe",
  "address": "123 Main St",
  "phone": "555-1234",
  "banking_details": "Bank Account: 12345678",
  "role": "Customer",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Create a Product:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/products/' \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Laptop",
    "base_price": 150000,
    "currency": "USD"
  }'
```
Response:
```json
{
  "id": 1,
  "description": "Laptop",
  "base_price": 150000,
  "currency": "USD",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Create an Order:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/' \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": 1,
    "status": "pending",
    "total_amount": 150000,
    "items": [
      {
        "product_id": 1,
        "quantity": 1,
        "unit_price": 150000,
        "total_price": 150000
      }
    ]
  }'
```
Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "pending",
  "total_amount": 150000,
  "invoice_id": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### Step 2: Order Staff Reviews and Accepts the Order

An Order Staff user is needed. Let's create one (or use an existing one). For simplicity, we'll create an Order Staff user.

**Create an Order Staff:**
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Jane Staff",
    "address": "456 Office St",
    "phone": "555-5678",
    "banking_details": "Bank Account: 87654321",
    "role": "Order Staff",
    "password": "staffpassword"
  }'
```
Response: (similar to customer, with role "Order Staff")

Now, accept the order (assuming order ID is 1):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/accept' \
  -H 'Content-Type: application/json'
```
Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "accepted",
  "total_amount": 150000,
  "invoice_id": null,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:01"
}
```

### Step 3: Accountant Creates an Invoice

Create an Accountant user:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Alice Accountant",
    "address": "789 Finance Ave",
    "phone": "555-9012",
    "banking_details": "Bank Account: 11223344",
    "role": "Accountant",
    "password": "accountantpassword"
  }'
```

Create invoice for order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/invoice' \
  -H 'Content-Type: application/json' \
  -d '{
    "billing_info": "John Doe, 123 Main St"
  }'
```
Response:
```json
{
  "id": 1,
  "order_id": 1,
  "billing_info": "John Doe, 123 Main St",
  "amount": 150000,
  "issue_date": "2024-01-01T00:00:01",
  "due_date": "2024-01-15T00:00:00",
  "status": "issued",
  "created_at": "2024-01-01T00:00:01",
  "updated_at": "2024-01-01T00:00:01"
}
```

### Step 4: Customer Pays the Invoice

Simulate payment (amount in cents):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/pay' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 150000,
    "method": "Credit Card"
  }'
```
Response:
```json
{
  "id": 1,
  "order_id": 1,
  "amount": 150000,
  "timestamp": "2024-01-01T00:00:02",
  "status": "pending",
  "method": "Credit Card"
}
```

### Step 5: Accountant Verifies the Payment

Verify payment (payment ID is 1):
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/payments/1/verify' \
  -H 'Content-Type: application/json'
```
Response:
```json
{
  "id": 1,
  "order_id": 1,
  "amount": 150000,
  "timestamp": "2024-01-01T00:00:02",
  "status": "verified",
  "method": "Credit Card"
}
```

### Step 6: Order Staff Ships the Paid Order

Ship order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/ship' \
  -H 'Content-Type: application/json'
```
Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "shipped",
  "total_amount": 150000,
  "invoice_id": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:03"
}
```

### Step 7: Order Staff Closes the Completed Order

Close order ID 1:
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/orders/1/close' \
  -H 'Content-Type: application/json'
```
Response:
```json
{
  "id": 1,
  "customer_id": 1,
  "status": "closed",
  "total_amount": 150000,
  "invoice_id": 1,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:04"
}
```

- Restart the application.
- Retrieve the order and verify its state is preserved and can proceed to the next step.

## 8. Troubleshooting

- **Database Connection Errors**: Check the `DATABASE_URL` environment variable and ensure the database is accessible.
- **Port Already in Use**: Change the port in the `uvicorn` command or stop the existing process on port 8000.
- **Module Not Found Errors**: Ensure you are in the virtual environment and have installed dependencies.

## 9. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 10. Support

For any issues or questions, please refer to the project documentation or contact the development team.

---
*Last updated: $(date)*