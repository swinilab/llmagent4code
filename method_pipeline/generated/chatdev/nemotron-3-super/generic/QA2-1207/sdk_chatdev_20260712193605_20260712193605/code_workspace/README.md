# Order Management System (OMS) Backend

A production-grade backend-only OMS for customer ordering, payment processing, invoicing, shipping, and closure.

## Features
- RESTful API with OpenAPI 3.0 documentation
- Role-based access (Customer, Order Staff, Accountant)
- Complete order lifecycle management
- Payment processing simulation
- Invoice generation
- Shipping tracking
- Order closure
- Designed for scalability and maintainability

## Architecture
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: SQLite (dev), configurable to PostgreSQL (prod)
- **Dependency Injection**: FastAPI Depends
- **API Versioning**: Path-based (/v1/)

## Project Structure
```
app/
├── main.py              # Application entry point
├── config.py            # Configuration (environment variables)
├── database.py          # SQLAlchemy setup
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas (request/response)
├── repositories.py      # Data access layer
├── services.py          # Business logic layer
└── controllers.py       # API endpoints (routers)
docs/
├── ADR-001-Architectural-Style.md
├── ADR-002-Database-Choice.md
├── ADR-003-Dependency-Injection.md
├── Data_Architecture.md
├── NFR_Traceability_Matrix.md
└── Shared_Domain_Models.md
requirements.txt
Dockerfile
```

## Local Deployment

### Prerequisites
- Python 3.11+
- Git
- Docker (optional, for containerized deployment)

### Option 1: Run Locally (without Docker)
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
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
6. Access the API at http://localhost:8000
7. View the interactive API documentation at http://localhost:8000/docs

### Option 2: Run with Docker
1. Build the image:
   ```bash
   docker build -t oms-backend .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 --name oms-app oms-backend
   ```
3. Access the API at http://localhost:8000

## API Documentation
Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Verification of Non-Functional Requirements (NFRs)

### NFR 2.1: Graceful Degradation
**How to verify:**
1. Start the application.
2. Use a load testing tool (e.g., Locust) to simulate high traffic on non-critical endpoints (e.g., `/api/v1/products`, `/api/v1/users`).
3. Monitor the response of critical endpoints (e.g., `/api/v1/orders`, `/api/v1/payments`, `/api/v1/invoices`).
4. Expected: Under extreme load, non-critical endpoints may return 503 (Service Unavailable) due to load shedding, while critical endpoints remain responsive (2xx/3xx).
5. Check server logs for load shedding events.

### NFR 2.2: Fault Detection and Recovery
**How to verify:**
1. Start the application and ensure it's connected to the database.
2. Stop the database container (if using Docker) or stop the SQLite file access (by renaming the file temporarily).
3. Observe the application logs for connection errors and retry attempts.
4. Restore the database.
5. Observe that the application reconnects and continues to serve requests without manual intervention.
6. Check that no data loss occurred for committed transactions.

### NFR 2.3: State Preservation
**How to verify:**
1. Create an order via the API (POST /api/v1/orders).
2. While the order is being processed (e.g., after acceptance but before payment), kill the application process (Ctrl+C or kill command).
3. Restart the application.
4. Retrieve the order via GET /api/v1/orders/{id}.
5. Verify that the order retains its state (e.g., status is "accepted") and can proceed to the next step (e.g., create invoice).
6. Ensure no committed data is lost.
## License
MIT