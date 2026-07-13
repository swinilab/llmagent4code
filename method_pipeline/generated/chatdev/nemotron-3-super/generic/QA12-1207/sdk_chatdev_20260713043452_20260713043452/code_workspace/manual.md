# Order Management System (OMS) Backend - User Manual

## 1. Introduction

This document serves as a user manual for the Order Management System (OMS) backend, a production-grade e-commerce order management system built with Python, FastAPI, and SQLAlchemy. The system provides RESTful APIs for managing customers, products, orders, payments, invoices, and shipping workflows.

## 2. Main Features

- **Customer Management**: Create, read, update, and delete customer profiles.
- **Product Catalog**: Manage product listings with pricing and descriptions.
- **Order Processing**: Full order lifecycle from creation to closure.
- **Payment Processing**: Record and verify payments.
- **Invoice Generation**: Create and manage invoices for orders.
- **Shipping Management**: Mark orders as shipped and track fulfillment.
- **RESTful API**: Versioned API with automatic OpenAPI (Swagger) documentation.
- **Dockerized**: Easy deployment using Docker Compose.
- **Designed for Concurrency**: Built with async/await for high performance.
- **Fault Tolerance**: Designed for graceful degradation and fault recovery.

## 3. System Requirements

- **Docker and Docker Compose** (for containerized deployment)
- **Git** (to clone the repository)
- **Python 3.9+** (for local development)
- **PostgreSQL** (for production; SQLite is used for development by default)

## 4. Installation

### 4.1 Using Docker (Recommended)

The simplest way to run the OMS is using Docker Compose, which sets up the application and a PostgreSQL database.

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oms
   ```

2. Build and start the containers:
   ```bash
   docker-compose up --build
   ```

3. The application will be available at `http://localhost:8000`.
   - API documentation: http://localhost:8000/docs
   - Alternative documentation (ReDoc): http://localhost:8000/redoc

### 4.2 Local Development (Without Docker)

For development or testing without Docker, you can run the application directly with Python.

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd oms
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the environment variables. Create a `.env` file in the `oms` directory (root directory (or modify the existing one) with at least:
   ```
   DATABASE_URL=sqlite+aiosqlite:///./oms.db
   ```
   For PostgreSQL, you can set:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
   ```

4. Apply database migrations:
   ```bash
   alembic upgrade head
   ```

5. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## 5. Running the Application

Once the application is running (via Docker or locally), you can access it at `http://localhost:8000`.

The API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 6. Using the API

The API follows REST conventions and is organized by resource:

- **Customers**: `/api/v1/customers`
- **Products**: `/api/v1/products`
- **Orders**: `/api/v1/orders`
- **Payments**: `/api/v1/payments`
- **Invoices**: `/api/v1/invoices`

### Example Workflow

Here's a typical order workflow using the API:

1. **Create a Customer**
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/customers' \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "John Doe",
       "address": "123 Main St",
       "phone": "555-1234",
       "banking_details": "Bank: XYZ, Account: 123456"
     }'
   ```

2. **Create a Product**
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/products' \
     -H 'Content-Type: application/json' \
     -d '{
       "description": "Sample Product",
       "base_price": 29.99,
       "currency": "USD"
     }'
   ```

3. **Create an Order** (assuming customer ID 1 and product ID 1)
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/orders' \
     -H 'Content-Type: application/json' \
     -d '{
       "customer_id": 1,
       "items": [
         {
           "product_id": 1,
           "quantity": 2
         }
       ]
     }'
   ```

4. **Process Payment** (assuming order ID 1)
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/payments' \
     -H 'Content-Type: application/json' \
     -d '{
       "order_id": 1,
       "amount": 59.98,
       "method": "credit_card",
       "transaction_id": "txn_123"
     }'
   ```

5. **Generate Invoice** (typically done by an accountant after order acceptance)
   ```bash
   curl -X 'POST' \
     'http://localhost:8000/api/v1/invoices' \
     -H 'Content-Type: application/json' \
     -d '{
       "order_id": 1,
       "billing_name": "John Doe",
       "billing_address": "123 Main St",
       "billing_email": "john@example.com",
       "billing_phone": "555-1234",
       "amount": 59.98,
       "issue_date": "2024-01-15",
       "due_date": "2024-02-15"
     }'
   ```

6. **Ship the Order** (order staff action)
   ```bash
   curl -X 'PATCH' \
     'http://localhost:8000/api/v1/orders/1' \
     -H 'Content-Type: application/json' \
     -d '{
       "status": "shipped"
     }'
   ```

7. **Close the Order**
   ```bash
   curl -X 'PATCH' \
     'http://localhost:8000/api/v1/orders/1' \
     -H 'Content-Type: application/json' \
     -d '{
       "status": "closed"
     }'
   ```

## 7. Verification of Non-Functional Requirements

Refer to the `VERIFICATION.md` file in the `oms` directory for detailed steps on how to verify each non-functional requirement (NFR), including:

- **NFR 1.1: Response Time** – Load testing with Locust or k6.
- **NFR 1.2: Concurrency & Resource Utilization** – Monitoring CPU, memory, and database connections under load.
- **NFR 1.3: Queue Management** – Simulating traffic spikes.
- **NFR 2.1: Graceful Degradation** – Testing under resource contention.
- **NFR 2.2: Fault Detection & Recovery** – Simulating database failures.
- **NFR 2.3: State Preservation** – Crash and recovery testing.

## 8. Database Migrations

The project uses Alembic for database migrations. To manage the database schema:

- Generate a new migration after model changes:
  ```bash
  alembic revision --autogenerate -m "description of changes"
  ```

- Apply pending migrations:
  ```bash
  alembic upgrade head
  ```

- Revert the last migration:
  ```bash
  alembic downgrade -1
  ```

When using Docker Compose, migrations are automatically applied on startup via the `prestart.sh` script.

## 9. Configuration

The application can be configured via environment variables. Key variables include:

- `PROJECT_NAME`: Name of the project (default: "Order Management System")
- `VERSION`: API version (default: "0.1.0")
- `DATABASE_URL`: Database connection string (default: `sqlite+aiosqlite:///./oms.db`)
- `DB_ECHO`: Set to `"True"` to enable SQLAlchemy echo (for debugging)
- `SECRET_KEY`: Secret key for JWT (if authentication is enabled)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time in minutes

These can be set in a `.env` file or passed via Docker Compose.

## 10. Troubleshooting

- **Application fails to start**: Check the Docker logs (`docker-compose logs app`) or console output for errors.
- **Database connection issues**: Verify the `DATABASE_URL` and ensure the database service is running.
- **API returns 500 errors**: Check the logs for stack traces; ensure database migrations are up to date.
- **Performance issues**: Monitor resource usage and consider increasing worker counts or using a production ASGI server like Gunicorn with Uvicorn workers.

## 11. Further Assistance

For more information, refer to the following files in the `oms` directory:

- `README.md`: Quick start overview.
- `ARCHITECTURE.md`: Detailed architectural decisions and NFR traceability.
- `DEPLOYMENT.md`: Detailed deployment instructions.
- `VERIFICATION.md`: Steps to verify non-functional requirements.
- API documentation: Swagger UI at `/docs` or ReDoc at `/redoc`.

---

*Manual generated for the Order Management System (OMS) backend.*